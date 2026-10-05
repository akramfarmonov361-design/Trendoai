"""
TrendoAI Live Audio va Ovozli AI muloqot xizmati.
"""
import asyncio
import base64
import io
import os
import shutil
import tempfile
import wave
from config import GEMINI_LIVE_MODEL, GEMINI_API_KEY
from utils.logger import setup_logger
logger = setup_logger("voice_service")



def get_gemini_api_key_candidates(extra_keys=None):
    """Mavjud barcha Gemini API kalitlari ro'yxati"""
    keys = []
    if extra_keys:
        for k in extra_keys:
            if k and k not in keys:
                keys.append(k)

    try:
        from flask import current_app, has_app_context
        if has_app_context() and current_app and current_app.config.get('GEMINI_API_KEY'):
            app_k = current_app.config.get('GEMINI_API_KEY').strip()
            if app_k and app_k not in keys:
                keys.append(app_k)
    except Exception:
        pass

    for env_k in [
        GEMINI_API_KEY,
        os.getenv('GEMINI_API_KEY'),
        os.getenv('GEMINI_API_KEY2'),
        os.getenv('GEMINI_API_KEY3'),
    ]:
        k = (env_k or '').strip()
        if k and k not in keys:
            keys.append(k)
    return keys


def get_ffmpeg_executable():
    """Tizimdagi ffmpeg yo'lini topish"""
    ffmpeg_path = shutil.which('ffmpeg')
    if ffmpeg_path:
        return ffmpeg_path

    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def convert_audio_for_live_api(audio_bytes, mime_type):
    """Audioni Live API uchun PCM formatga o'tkazish"""
    normalized_mime = (mime_type or '').split(';', 1)[0].lower()
    if normalized_mime == 'audio/pcm':
        return audio_bytes, mime_type or 'audio/pcm;rate=16000'

    ffmpeg_path = get_ffmpeg_executable()
    if not ffmpeg_path:
        return audio_bytes, mime_type

    import subprocess

    suffix_by_mime = {
        'audio/webm': '.webm',
        'audio/ogg': '.ogg',
        'audio/mpeg': '.mp3',
        'audio/mp3': '.mp3',
        'audio/mp4': '.m4a',
        'audio/wav': '.wav',
        'audio/x-wav': '.wav',
    }
    input_path = None
    output_path = None

    try:
        with tempfile.NamedTemporaryFile(suffix=suffix_by_mime.get(normalized_mime, '.audio'), delete=False) as source_file:
            source_file.write(audio_bytes)
            input_path = source_file.name

        with tempfile.NamedTemporaryFile(suffix='.pcm', delete=False) as output_file:
            output_path = output_file.name

        subprocess.run(
            [
                ffmpeg_path,
                '-hide_banner',
                '-loglevel',
                'error',
                '-y',
                '-i',
                input_path,
                '-ac',
                '1',
                '-ar',
                '16000',
                '-f',
                's16le',
                output_path,
            ],
            check=True,
            capture_output=True,
        )

        with open(output_path, 'rb') as converted_file:
            converted = converted_file.read()

        if converted:
            return converted, 'audio/pcm;rate=16000'
    except Exception as exc:
        logger.error(f"[voice] Audio conversion for Gemini Live failed: {exc}")
    finally:
        for path in [input_path, output_path]:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError:
                    pass

    return audio_bytes, mime_type


def audio_chunks_to_wav_base64(chunks):
    """Audio bo'laklarini WAV base64 satriga aylantirish"""
    if not chunks:
        return None

    wav_io = io.BytesIO()
    with wave.open(wav_io, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(24000)
        for chunk in chunks:
            if isinstance(chunk, str):
                chunk = base64.b64decode(chunk)
            wav_file.writeframes(bytes(chunk))

    return base64.b64encode(wav_io.getvalue()).decode('utf-8')


def chat_audio_system_prompt():
    return """Siz TrendoAI AI assistentisiz.
Vazifangiz:
1. O'zbek tilida, judayam qisqa, londa (maksimum 1-2 ta qisqa jumla) va do'stona javob bering.
2. Ovozli muloqot tez bo'lishi uchun javobni cho'zmang va ortiqcha gapirmang.
3. TrendoAI xizmatlari: Telegram Botlar, Web Saytlar, AI Chatbotlar."""


async def _generate_live_audio_reply(audio_bytes, mime_type, system_prompt):
    try:
        from google import genai as new_genai
        from google.genai import types as new_types
    except ImportError as exc:
        raise RuntimeError("google-genai kutubxonasi o'rnatilmagan") from exc

    live_audio, live_mime_type = convert_audio_for_live_api(audio_bytes, mime_type)
    config = new_types.LiveConnectConfig(
        response_modalities=[new_types.Modality.AUDIO],
        system_instruction=system_prompt,
        speech_config=new_types.SpeechConfig(
            voice_config=new_types.VoiceConfig(
                prebuilt_voice_config=new_types.PrebuiltVoiceConfig(voice_name='Zephyr')
            )
        ),
    )

    last_error = None
    for index, key in enumerate(get_gemini_api_key_candidates(), start=1):
        try:
            client = new_genai.Client(api_key=key, http_options={"api_version": "v1beta"})
            audio_chunks = []
            model_text_parts = []
            output_transcript_parts = []
            input_transcript_parts = []

            model_target = GEMINI_LIVE_MODEL
            if not model_target.startswith('models/'):
                model_target = f"models/{model_target}"

            async with client.aio.live.connect(model=model_target, config=config) as session:
                blob = new_types.Blob(data=live_audio, mime_type=live_mime_type or 'audio/webm')
                if hasattr(session, 'send_realtime_input'):
                    await session.send_realtime_input(audio=blob)
                    await session.send_realtime_input(audio_stream_end=True)
                elif hasattr(session, 'send'):
                    await session.send(input={"data": live_audio, "mime_type": live_mime_type or 'audio/webm'}, end_of_turn=True)
                else:
                    await session.send_client_content(
                        turns=new_types.Content(
                            role='user',
                            parts=[new_types.Part(inline_data=blob)],
                        ),
                        turn_complete=True,
                    )

                async for response in session.receive():
                    raw_data = getattr(response, 'data', None)
                    if raw_data:
                        audio_chunks.append(raw_data)

                    raw_text = getattr(response, 'text', None)
                    if raw_text:
                        model_text_parts.append(raw_text)

                    server_content = getattr(response, 'server_content', None)
                    if server_content is not None:
                        input_transcription = getattr(server_content, 'input_transcription', None)
                        if input_transcription and getattr(input_transcription, 'text', None):
                            input_transcript_parts.append(input_transcription.text)

                        output_transcription = getattr(server_content, 'output_transcription', None)
                        if output_transcription and getattr(output_transcription, 'text', None):
                            output_transcript_parts.append(output_transcription.text)

                        model_turn = getattr(server_content, 'model_turn', None)
                        if model_turn and model_turn.parts:
                            for part in model_turn.parts:
                                if getattr(part, 'text', None):
                                    model_text_parts.append(part.text)
                                inline_data = getattr(part, 'inline_data', None)
                                if inline_data and getattr(inline_data, 'data', None):
                                    audio_chunks.append(inline_data.data)

            response_text = ''.join(output_transcript_parts).strip() or ''.join(model_text_parts).strip()
            audio_base64_result = audio_chunks_to_wav_base64(audio_chunks)
            if response_text or audio_base64_result:
                return {
                    'text': response_text,
                    'audio_base64': audio_base64_result,
                    'input_transcription': ''.join(input_transcript_parts).strip(),
                    'model': GEMINI_LIVE_MODEL,
                }
        except Exception as exc:
            last_error = exc
            logger.error(f"[voice] Gemini Live audio failed on key #{index}: {type(exc).__name__}: {str(exc)[:160]}")

    raise last_error if last_error else RuntimeError("Gemini Live API kaliti topilmadi")


def get_live_audio_reply(audio_bytes, mime_type='audio/webm', system_prompt=None):
    """Sinxron kontekstdan Gemini Live ovozli javobini olish"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            _generate_live_audio_reply(
                audio_bytes=audio_bytes,
                mime_type=mime_type,
                system_prompt=system_prompt or chat_audio_system_prompt(),
            )
        )
    finally:
        loop.close()


def friendly_audio_error(exc):
    """Ovozli xatoliklar uchun tushunarli matn"""
    message = str(exc).lower()
    if 'denied access' in message or 'permission' in message or '403' in message or '1008' in message:
        return "Gemini Live uchun API project access yoqilmagan. Iltimos, matn yozib yuboring yoki Telegram orqali bog'laning: @trendoai"
    if 'quota' in message or 'resourceexhausted' in message or '429' in message:
        return "Gemini API limiti tugagan. Iltimos, matn yozib yuboring yoki birozdan keyin qayta urinib ko'ring."
    return "Gemini Live ovozni qayta ishlay olmadi. Iltimos, savolingizni matn qilib yozing yoki Telegram orqali bog'laning: @trendoai"

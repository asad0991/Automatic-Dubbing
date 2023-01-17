filepath = ""
input_filepath="static/uploads/"
output_filepath = "~/Transcripts/"
bucketname = "dubbing-speech-to-text-bucket"
from googletrans import Translator
from pydub import AudioSegment
import io
import os
from google.cloud import speech
import wave
from google.cloud import storage
import google.cloud.texttospeech as tts
from pytube import YouTube
import moviepy.editor as mp
from ssml_builder.core import Speech

def video_download_from_link(filename,url: str=None, outpath: str = "./"):

    #yt = YouTube(url)

    # yt.streams.filter(file_extension="mp4").get_by_resolution("360p").download(outpath,filename='motiv.mp4')

    my_clip = mp.VideoFileClip(input_filepath + filename)
    my_clip
    my_clip.audio.write_audiofile("motiv.wav")



def stereo_to_mono(audio_file_name):
    sound = AudioSegment.from_wav(audio_file_name)
    sound = sound.set_channels(1)
    sound.export(audio_file_name, format="wav")


def frame_rate_channel(audio_file_name):
    with wave.open(audio_file_name, "rb") as wave_file:
        frame_rate = wave_file.getframerate()
        channels = wave_file.getnchannels()
        return frame_rate,channels



def upload_blob(bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to the bucket."""
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(source_file_name)

def delete_blob(bucket_name, blob_name):
    """Deletes a blob from the bucket."""
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)

    blob.delete()


def audio_to_text(audio_file_name,original_language,target_language):
    file_name = filepath + audio_file_name
    frame_rate, channels = frame_rate_channel(file_name)
    if channels > 1:
        stereo_to_mono(file_name)

    bucket_name = bucketname
    source_file_name = filepath + audio_file_name
    destination_blob_name = audio_file_name

    upload_blob(bucket_name, source_file_name, destination_blob_name)

    gcs_uri = 'gs://' + bucketname + '/' + audio_file_name
    transcript = ''

    client = speech.SpeechClient()
    audio = speech.RecognitionAudio(uri=gcs_uri)

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=frame_rate,
        language_code=original_language,
        enable_word_time_offsets=True,
    )

    operation = client.long_running_recognize(config=config, audio=audio)
    response = operation.result(timeout=10000)

    for result in response.results:
        transcript += result.alternatives[0].transcript

    delete_blob(bucket_name, destination_blob_name)
    stamp = 0.0
    sp = Speech()
    sentence = ''
    for result in response.results:
        alternative = result.alternatives[0]
        for word_info in alternative.words:
            word = word_info.word
            start_time = word_info.start_time
            end_time = word_info.end_time
            if stamp == 0.0 :
                sp.pause(time=end_time.total_seconds())
                stamp = end_time.total_seconds()
                sentence += word
            elif stamp == start_time.total_seconds():
                sentence+=' '+word
                stamp = end_time.total_seconds()
            elif stamp != start_time.total_seconds():
                sentence=text_translation(sentence,original_language,target_language)
                sp.add_text(sentence)
                sp.pause(time=start_time.total_seconds() - stamp)
                sentence=''
                sentence+=word
                stamp = end_time.total_seconds()
    sentence = text_translation(sentence,original_language,target_language)
    sp.add_text(sentence)
    ssml = sp.speak()
    return ssml


def text_translation(content,original_language,target_language):
    original_language=original_language.split('-',1)
    target_language=target_language.split('-',1)
    print(original_language)
    print(target_language)
    file_translate = Translator()
    result = file_translate.translate(content, dest=target_language[0], src=original_language[0])

    print(result.text)

    res = result.text
    a = open("urdu.txt", "w+", encoding='utf-8')
    a.write(res)
    return res

def text_to_audio(voice_name: str, text: str,video_file):
    language_code = "-".join(voice_name.split("-")[:2])
    text_input = tts.SynthesisInput(ssml=text)
    voice_params = tts.VoiceSelectionParams(
        language_code=language_code, name=voice_name, ssml_gender=tts.SsmlVoiceGender.NEUTRAL
    )
    audio_config = tts.AudioConfig(audio_encoding=tts.AudioEncoding.LINEAR16, speaking_rate=0.8)

    client = tts.TextToSpeechClient()
    response = client.synthesize_speech(
        input=text_input, voice=voice_params, audio_config=audio_config
    )

    filename = f"{language_code}.wav"
    with open(filename, "wb") as out:
        out.write(response.audio_content)
        print(f'Generated speech saved to "{filename}"')
    audio= mp.AudioFileClip(filename)
    my_clip = mp.VideoFileClip( input_filepath + video_file )
    new=my_clip.without_audio()
    new = new.set_audio(audio)
    new.write_videofile("dubbed-" + video_file, fps=30, threads=1, codec="libx264" )
    return "dubbed-" + video_file

def dub_video(filename,original_language,target_langauge):
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'google_secret_key.json'
    video_download_from_link(filename)
    return text_to_audio(target_langauge, audio_to_text("motiv.wav",original_language,target_langauge),filename)


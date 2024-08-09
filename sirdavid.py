import asyncio
import base64
import datetime
import logging
import os
import random
import re
import ssl
import uuid
import websockets
from io import BytesIO
from elevenlabs.client import ElevenLabs
from elevenlabs import save
from google.cloud import storage
from openai import OpenAI

script = []

# gcp bucket info
bucket_name = os.environ.get('SIRDAVID_BUCKET')
service_account_file = os.environ.get('SIRDAVID_SERVICEACCOUNT_JSON')

# setup logging
logging.basicConfig(
    filename="sirdavid.log",  # File to save logs
    level=logging.INFO,  # Minimum level to log (inclusive)
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",  # Log message format
)
logger = logging.getLogger(__name__)

# analyse_image()
def analyse_image(base64_image, script):
  # create openai client
  api_key = os.environ.get('OPENAI_API_KEY')
  api_gw = os.environ.get('SIRDAVID_APIGW')
  # use "https://api.openai.com/v1" for default openai base_url 
  client = OpenAI(api_key=api_key, base_url=api_gw)

  response = client.chat.completions.create(
  model="gpt-4o",
  messages=[
    {
      "role": "user",
      "content": [
        {"type": "text", 
         "text": "You are Sir David Attenborough. Describe and narrate this image as if it is a nature documentary. Make it snarky and funny. Don't repeat yourself. Make it short and snappy. If there is a human in the image that does anything remotely interesting, make a big deal about it!"},
        {
          "type": "image_url",
          "image_url": {
            "url": f"data:image/jpeg;base64,{base64_image}"
          },
        },
      ],
    }
  ],
  max_tokens=300,
  )

  response_text = response.choices[0].message.content
  return response_text

# contains_sorry()
def contains_sorry(text):
  # if openai's text reponse contains a "sorry" of any kind, the analysis was no good
  return "sorry".lower() in text.lower()

# decode_image()
def decode_image(data):
  try:
    # extract base64 encoded data (assumption: png data starts with 'data:image/png;base64')
    prefix, encoded_data = data.split(",", 1)
    if prefix != "data:image/png;base64":
      raise ValueError("Invalid image data format")

    # looks good, we have a png, decode it
    decoded_data = base64.b64decode(encoded_data)
  except (ValueError, IndexError) as e:
    raise ValueError("Error processing image data:", e)

  # create a BytesIO object from decoded data
  image_buffer = BytesIO(decoded_data)

  try:
    from PIL import Image
    # open the image from the BytesIO object
    return Image.open(image_buffer)
  except ImportError:
    raise ImportError("PIL library not installed. Please install it using 'pip install Pillow'")

# generate_audio()
def generate_audio(text, david_id):
  # elevenlabs client
  api_key = os.environ.get('ELEVENLABS_API_KEY')
  elclient = ElevenLabs(api_key=api_key)

  # generate the audio
  voice = os.environ.get('SIRDAVID_VOICE')
  # strip any commentary from openai in square brackets
  modified_text = re.sub(r'\[.*?\]', '', text)
  # new_text = "<break time=\"1.5s\" /> " + modified_text
  new_text = "-- --" + modified_text
  audio = elclient.generate(text=new_text, voice=voice, model="eleven_multilingual_v2")

  # write audio file to local disk
  filename = david_id + ".mp3"
  save(audio, filename)
  
  logger.info(f"rx audio from elevenlabs")

  # write audio file to gcp
  save_in_gcp(filename, "audio/mp3")

# save_in_gcp()
def save_in_gcp(filename, type):
  # client
  storage_client = storage.Client.from_service_account_json(service_account_file)
  bucket = storage_client.bucket(bucket_name)
  blob = bucket.blob(filename)

  # upload
  blob.upload_from_filename(filename, content_type=type)
  logger.info(f"tx {filename} to gcp bucket")

# websocket_handler()
async def websocket_handler(websocket, path):
  # get remote info
  remote_ip, port = websocket.remote_address
  logger.info(f"rx hello from {remote_ip}")
  
  # send hello to remote
  message = "Please click the \"Take Photo\" button to upload a webcam photo to Sir David!!"
  await websocket.send(message)
  logger.info(f"tx hello to {remote_ip}")

  # process message from remote
  async for message in websocket:
    try:
      # was an image sent? try to decode it
      image = decode_image(message)
      if image:
        # we have a valid image, process it
        fname = f"{uuid.uuid4()}"
        filename = fname + ".png"
        logger.info(f"rx image from {remote_ip}")
        
        # save image locally
        image.save(filename)
        # save image in gcp
        save_in_gcp(filename, "image/png")

        # inform remote that we are processing the image
        await websocket.send("Thankyou! Sir David has received your photo and is analysing it now. Please stand by...")

        # open the image and send base64-encoded version of it to openai for analysis
        with open(filename, "rb") as image_file:
          base64_image = base64.b64encode(image_file.read()).decode("utf-8")
        analysis = analyse_image(base64_image, script=script)
        logger.info(f"rx analysis from openai")

        # does the analysis contain an error?
        if contains_sorry(analysis):
          logger.error(f"error analysing {filename}, error={analysis} ")
          await websocket.send("Oops, there was a problem -- please try again!")
        else:
          # analysis is good
          await websocket.send("Analysis complete, generating audio...")
          # save analysis locally
          filename = fname + ".txt"
          with open(filename, "wb") as file:
              file.write(analysis.encode("UTF-8"))
          
          # save analysis text in gcp
          save_in_gcp(filename, "text/plain")

          # generate the audio
          generate_audio(analysis, fname)
          
          # send audio url to remote
          url = "https://storage.googleapis.com/davidattenborough/" + fname + ".mp3"
          await websocket.send(url)

          # send analysis to remote
          await websocket.send(analysis)

          # finished
          logger.info(f"tx audio to {remote_ip}")
    except (ValueError, ImportError) as e:
      # debug
      if message == "PING" or message == "ping":
          await websocket.send("PONG")     
                             
# main()
async def main():
  # ssl setup for secure websocket
  ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
  ssl_cert = os.environ.get('SIRDAVID_SSL_CERT')
  ssl_key = os.environ.get('SIRDAVID_SSL_KEY')
  ssl_context.load_cert_chain(ssl_cert, keyfile=ssl_key)

  # start secure websocket server
  port = os.environ.get('SIRDAVID_PORT')
  async with websockets.serve(websocket_handler, "0.0.0.0", port, ssl=ssl_context):
      await asyncio.Future()  # run forever

# LFG
if __name__ == "__main__":
    asyncio.run(main()) 

# EOF

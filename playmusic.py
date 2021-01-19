
import time
import uuid
import soco
import requests
import appsettings
import usersettings

def playmediastation(sonosroom_local, receivedtext):

  # extract info
  tokens = receivedtext.split(':')
  artist = tokens[1]
  album = tokens[2]

  # connect to mediastation
  try:
    url = usersettings.mediastation + '/browse/search/tracks?artist=' + artist + '&album=' + album
    r = requests.get(url)
  except:
    print("Failed to connect to Mediastation at " + url)
    return False

  # check this is a list of tracks
  r = r.json()
  if r is None or len(r) == 0 or r[0]['type'] != 'audio':
    print("Failed to search in Mediastation at " + url)
    return False

  # now send orders to sonos
  for zone in soco.discover():
    if zone.player_name.lower() == sonosroom_local.lower():
      
      print('Clearing Sonos queue')
      zone.clear_queue()

      print('Adding Mediastation items to queue')
      for item in r:
        zone.add_uri_to_queue(item['upnp_url'])

      print('Playing')
      zone.play()

  # 1st clear queue
  #requests.get(usersettings.sonoshttpaddress + "/" + sonosroom_local + "/clearqueue")


  return True



def playtag(sonosroom_local, receivedtext):

  receivedtext_lower = receivedtext.lower()
  servicetype = ""

  # mediastation
  if receivedtext_lower.startswith('mediastation:'):
    return playmediastation(sonosroom_local, receivedtext)

  # check if a full HTTP URL read from NFC
  if receivedtext_lower.startswith('http'):
    servicetype = "completeurl"
    sonosinstruction = receivedtext

  # determine which music service read from NFC
  if receivedtext_lower.startswith('spotify'):
    servicetype = "spotify"
    sonosinstruction = "spotify/now/" + receivedtext

  if receivedtext_lower.startswith('tunein'):
    servicetype = "tunein"
    sonosinstruction = receivedtext

  if receivedtext_lower.startswith('amazonmusic:'):
    servicetype = "amazonmusic"
    sonosinstruction = "amazonmusic/now/" + receivedtext[12:]

  if receivedtext_lower.startswith('apple:'):
    servicetype = "applemusic"
    sonosinstruction = "applemusic/now/" + receivedtext[6:]

  if receivedtext_lower.startswith('applemusic:'):
    servicetype = "applemusic"
    sonosinstruction = "applemusic/now/" + receivedtext[11:]

  # check if a Sonos "command" from NFC
  if receivedtext_lower.startswith('command'):
    servicetype = "command"
    sonosinstruction = receivedtext[8:]

  # if no service or command detected, exit
  if servicetype == "":
    print("Service type not recognised. NFC tag text should begin spotify, tunein, amazonmusic, apple/applemusic, command or room.")
    if usersettings.sendanonymoususagestatistics == "yes":
      r = requests.post(appsettings.usagestatsurl, data={'time': time.time(
      ), 'value1': appsettings.appversion, 'value2': hex(uuid.getnode()), 'value3': 'invalid service type sent'})
    return False

  print("Detected " + servicetype + " service request")

  # build the URL we want to request
  if servicetype.lower() == 'completeurl':
    urltoget = sonosinstruction
  else:
    urltoget = usersettings.sonoshttpaddress + "/" +  sonosroom_local + "/" + sonosinstruction

  # check Sonos API is responding
  try:
    r = requests.get(usersettings.sonoshttpaddress)
  except:
    print("Failed to connect to Sonos API at " + usersettings.sonoshttpaddress)
    return False

  # clear the queue for every service request type except commands
  if servicetype != "command":
    print("Clearing Sonos queue")
    r = requests.get(usersettings.sonoshttpaddress + "/" + sonosroom_local + "/clearqueue")

  # use the request function to get the URL built previously, triggering the sonos
  print("Fetching URL via HTTP: " + urltoget)
  r = requests.get(urltoget)

  if r.status_code != 200:
    print("Error code returned from Sonos API")
    return False

  print("Sonos API reports " + r.json()['status'])

  # put together log data and send (if given permission)
  if usersettings.sendanonymoususagestatistics == "yes":
    logdata = {
      'time': time.time(),
      'value1': appsettings.appversion,
      'value2': hex(uuid.getnode()),
      'actiontype': 'nfcread',
      'value3': receivedtext,
      'servicetype': servicetype,
      'urltoget': urltoget
    }
    r = requests.post(appsettings.usagestatsurl, data=logdata)

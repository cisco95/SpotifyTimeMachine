from spotipy.oauth2 import SpotifyOAuth
from datetime import datetime
from bs4 import BeautifulSoup
import requests
import spotipy
import base64
import json
import os

CLI_ID = os.environ['CLIENT_ID']
CLI_SECRET = os.environ['CLIENT_SECRET']
MYSPOTIFYURL = os.environ['MYSPOTIFYURL']
URL = "https://accounts.spotify.com/api/token"
URL_SEARCH = "https://api.spotify.com/v1/search"
SCOPE = "playlist-modify-private playlist-modify-public"


def get_date():
  '''
  Requests date from user following specified format. If not valid date following format provided, asks again. 
  '''
  date_selected = input(
    "Which year do you want to travel to? (format: YYYY-MM-DD)\n")
  try:
    datetime_object = datetime.strptime(date_selected, '%Y-%m-%d')
    return date_selected
  except Exception as e:
    print("ERROR: Invalid date format.")
    print(e)
    return get_date()


def get_token():
  '''
  Returns authentication token for use with requests to spotify. 
  '''
  auth_string = f"{CLI_ID}:{CLI_SECRET}"
  auth_bytes = auth_string.encode("utf-8")
  auth_base64 = str(base64.b64encode(auth_bytes), "utf-8")
  headers = {
    "Authorization": "Basic " + auth_base64,
    "Content-Type": "application/x-www-form-urlencoded",
  }

  data = {
    "grant_type": "client_credentials",
  }

  response = requests.post(URL, headers=headers, data=data)
  json_response = json.loads(response.content)
  token = json_response["access_token"]

  return token


def get_songs_by_artist(token, artist_name, song_title):
  '''
  Returns the song URI based on the artist/song title search. 
  '''
  # *** Issue: this currently works, but excludes a lot of songs since first song is not 
  # the one by the artist in question. Need to tweak so that if the first song is not the 
  # correct one, then look at subsequent options.

  # *** Issue: Currently works, but some artists names are different and would work better 
  # with ID. ie, NSYNC is listed as *NSYNC on spotify, but 'N SYNC on hot 100 list. causes issue.

  # POSSIBLE SOLUTIONS:
  # do ID first and if no results, then do by name?
  # use "".join(ch for ch in badString if ch.isalnum()) to make string with only alphanumeric 
  # characters and compare like that?

  # *** Solution:  too complicated, but in turn found that searching is much easier and more 
  # accurate if you provide both the name and the title in a single query separated by spaces. 
  # Even if the name does not exactly match, the API will likely still return the correct song 
  # in the first position. Only need to look at items[0] now instead of searching through.

  headers = {"Authorization": "Bearer " + token}
  data = {
    "q": song_title + " " + artist_name,
    "type": "track",
    "limit": 1,
  }

  response = requests.get(URL_SEARCH, params=data, headers=headers)

  song = json.loads(response.content)["tracks"]["items"][0]
  try:

    song_URI = song['uri']
    return song_URI

  except:
    print(
      f"No songs found with: \n\tArtist ID: {artist_name}\n\tSong Title: {song_title}"
    )
    return 0


def create_song_URI_list(hot_100_list):
  '''
  Creates a list of song URIs using the hot 100 list and get_songs_by_artist function. 
  '''
  song_URI_list = []
  token = get_token()
  for (song, artist) in hot_100_list:
    song_URI = get_songs_by_artist(token, artist, song)

    if song_URI:
      song_URI_list.append(song_URI)

  return song_URI_list


def create_playlist(uri_list):
  '''
  Creates a public spotify playlist and adds songs from Billboard Top 100. 
  '''

  sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=SCOPE,
                                                 client_id=CLI_ID,
                                                 client_secret=CLI_SECRET,
                                                 redirect_uri=MYSPOTIFYURL,
                                                 show_dialog=True,
                                                 cache_path="token.txt"))
  current_user = sp.current_user()["id"]

  new_playlist = sp.user_playlist_create(
    user=current_user, name=f"Billboard Hot 100: {year_selected}", public=True)

  sp.user_playlist_add_tracks(user=current_user,
                              playlist_id=new_playlist["id"],
                              tracks=uri_list)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
year_selected = get_date()

# *** Future improvements: Check date, see if there is already a playlist that exists in the 
# account. If exists, provide link to playlist. Otherwise, continue.

# *** Future improvements: Input Validation: check that the date provided exists only between 
# the dates that billboard can provide

response = requests.get(
  f"https://www.billboard.com/charts/hot-100/{year_selected}")
resp = response.text
soup = BeautifulSoup(resp, 'html.parser')

titles = soup.select("h3#title-of-a-story.c-title.a-no-trucate")
artists = soup.select("span.c-label.a-no-trucate")
hot_100_list = []

for i in range(len(artists)):
  hot_100_list.append((titles[i].text.strip(), artists[i].text.strip()))

token = get_token()

uri_list = create_song_URI_list(hot_100_list)

create_playlist(uri_list)

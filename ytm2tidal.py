import re
import tidalapi
from ytmusicapi import YTMusic as ytmusicapi
import os
from dotenv import load_dotenv
from mutagen.flac import FLAC, Picture
from mutagen.mp4 import MP4, MP4Cover
import urllib.request
from pathlib import Path
import threading
from time import sleep
import yaml
from ytmusicapi.auth.oauth import OAuthCredentials

""" Multiprocessing is useless because its excessive speed generates 
a 429 error on Tidal servers (Too Many Requests for url). """
# import multiprocess as mp


class ytm2tidal:
    def __init__(self):
        load_dotenv()
        self._config = self._openConfig()
        self._tidal = TidalManager()
        self._ytmusic = YTMusicManager("oauth.json")
        self._successCounter, self._failureCounter = 0, 0
        self._processAllTracks()

    def _openConfig(self) -> dict:
        """
        Open config file
        """
        with open('config.yml', 'r') as file:
            return yaml.safe_load(file)

    def _tryProcessTrack(self, title: str, artists: list[str], artist: str = None) -> int:
        """
        Try to search and add a track to favorites
        """
        response = self._tidal.searchAndAddTrackToFavorites(title, artists, self._config, artist)
        if response == 1 or response == 2 :
            return response
        nofeatTitle = re.sub(" \( *feat\.? +[^)]+\) *", "", title)
        if nofeatTitle != title:
            print(
                "⚠ Nothing found. Trying again without any featuring artists in title.")
            response = self._tidal.searchAndAddTrackToFavorites(nofeatTitle, artists, self._config, artist)
            if response == 1 or response == 2:
                return response
        cleanTitle = re.sub("[\(\[].*?[\)\]]", "", title)
        if cleanTitle != title:
            print(
                "⚠ Nothing found. Trying again without parentheses and brackets in title.")
            response = self._tidal.searchAndAddTrackToFavorites(cleanTitle, artists, self._config, artist)
            if response == 1 or response == 2 :
                return response
        return 0

    def _processTrack(self, ytmTrackInfo: dict) -> bool:
        """
        Process track
        """
        ytmTrackArtists = [artist["name"] for artist in ytmTrackInfo["artists"]
                           ] if ytmTrackInfo["artists"] != None else ["<No artist provided>"]
        print("---\n⏳ Processing '" +
              ytmTrackInfo["title"] + "' by '" + ', '.join(ytmTrackArtists) + "' (from YTMusic)")
        if ytmTrackArtists[0] != "<No artist provided>":
            for ytmTrackArtist in ytmTrackArtists:
                print("🏷 Trying with '" + ytmTrackArtist + "' artist name.")
                response = self._tryProcessTrack(ytmTrackInfo["title"], ytmTrackArtists, ytmTrackArtist)
                if response == 1 or response == 2 :
                    self._successCounter += 1
                    if response == 1 :
                        print("✅ Successfully processed track.")
                    else:
                        print("🆗 Track is already in Tidal favorites")
                    return True
        print("🏷 Trying without any artist name")
        response = self._tryProcessTrack(ytmTrackInfo["title"], ytmTrackArtists)
        if response == 1 or response == 2 :
            self._successCounter += 1
            if response == 1 :
                print("✅ Successfully processed track.")
            else:
                print("🆗 Track is already in Tidal favorites.")
            return True
        self._failureCounter += 1
        print("❌ Found nothing. Skipping track.")
        return False

    def _processAllTracks(self):
        """
        Process all tracks
        """
        ytmLikedTracks = self._ytmusic.likedTracks["tracks"][:self._ytmusic.likedTracksLimit]

        """ Multiprocessing is useless because its excessive speed generates 
        a 429 error on Tidal servers (Too Many Requests for url). """
        """ with mp.Pool(processes = mp.cpu_count()) as pool:
            pool.map(self._processTrack, ytmLikedTracks) """

        for likedTrack in reversed(ytmLikedTracks):
            self._processTrack(likedTrack)
            sleep(0.8) # Avoid 429 error on Tidal servers when downloading tracks, I can't get any faster than this

        print("---------\n---------\n📋 Processed " + str(self._successCounter + self._failureCounter) +
              " tracks. (" + str(self._successCounter) + " succeeded / " + str(self._failureCounter) + " failed)")


class TidalManager(ytm2tidal):
    def __init__(self):
        self._download = self._askForDownloading()
        self._session = tidalapi.Session()
        self._session.login_oauth_simple()
        self._session.audio_quality = tidalapi.Quality.hi_res_lossless
        self._favorites = self._getFavorites()

    def _askForDownloading(self) -> bool:
        """
        Asks user if he wants to download the tracks
        """
        try:
            answer = input("❓ Would you like to download the tracks? [Y/N]: ")
            assert answer.lower() in ["y", "n"]
            if answer.lower() == "y":
                print("✅ The program will download the tracks under the ./tracks/ folder.")
                Path("./tracks/").mkdir(parents=True, exist_ok=True)
                return True
            elif answer.lower() == "n":
                print("❌ The program won't download tracks.")
                return False
        except (ValueError, AssertionError):
            return self._askForDownloading()

    def _searchTrack(self, query: str) -> tidalapi.media.Track | None:
        """
        Search track on Tidal with API
        """
        print("🔎 Searching track on Tidal (Query : " + query + ")")
        return self._session.search(query, [tidalapi.media.Track])

    def _addTrackToFavorites(self, track: tidalapi.media.Track) -> None:
        """
        Add a track to favorites on Tidal with API
        """
        print("➕ Track found on Tidal. Adding '" + track.full_name +
              "' by '" + track.artists[0].name + "' to favorites on Tidal.")
        self._favorites.add_track(track.id)

    def searchAndAddTrackToFavorites(self, title: str, artists : list[str], config: dict, artist: str = None) -> int:
        """
        Search track and add it to favorites if found
        """
        tidalSearch = self._searchTrack(
            title if artist is None else title + " " + artist)
        tidalTrackList = tidalSearch["tracks"]
        tidalTrackList = self._removeBlacklistedTracks(tidalTrackList, config['Blacklist'])
        if len(tidalTrackList) != 0 :
            bestTrack = self._bestTidalSearchResult(tidalTrackList, title, artists)
            if bestTrack.id not in [track.id for track in self._favorites.tracks()] :
                self._addTrackToFavorites(bestTrack)
                if self._download :
                    self._downloadTrack(bestTrack)
                return 1
            else :
                if self._download and config["DownloadFavorites"]:
                    self._downloadTrack(bestTrack)
                return 2
        return 0
    
    def _removeBlacklistedTracks(self, tracks: list[tidalapi.media.Track], blacklist: dict) -> list[tidalapi.media.Track]:
        """
        Remove blacklisted tracks from a list of tracks
        """
        if blacklist['Enabled'] :
            clearedTracks = []
            for track in tracks :
                if self._isTrackArtistWhitelisted(track, blacklist) and self._isTrackStringWhitelisted(track, blacklist) :
                    clearedTracks.append(track)
            return clearedTracks
        else :
            return tracks
        
    def _isTrackArtistWhitelisted(self, track: tidalapi.media.Track, blacklist: dict) -> bool :
        """
        Check if a track isn't on the blacklist
        """
        if len(blacklist['Artists']) == 0 :
            return True
        trackArtists = [artist.name for artist in track.artists]
        if self._rateOfCommonElements(blacklist['Artists'], trackArtists) != 0 :
            return False
        return True
    
    def _isTrackStringWhitelisted(self, track: tidalapi.media.Track, blacklist: dict) -> bool :
        """
        Check if every string in the blacklist isn't in the track's name
        """
        if len(blacklist['Strings']) == 0 :
            return True
        for string in blacklist['Strings'] :
            if string in track.full_name :
                return False
        return True

    def _downloadTrack(self, track):
        """
        Download tidal track
        """
        print("⬇️ Downloading track (in parallel processing)")
        try:
            self._session.audio_quality = tidalapi.Quality.hi_res_lossless
            trackUrl = track.get_url()
        except: # We need this to fix how tidalapi handles audio quality for now (MQA/HIRES deprecated)
            sleep(0.8) # Avoid rate limiting
            try:
                print("❌ Can't download in FLAC HIRES audio quality, trying MQA")
                self._session.audio_quality = tidalapi.Quality.hi_res
                trackUrl = track.get_url()
            except:
                sleep(0.8) # Avoid rate limiting
                print("❌ Can't download in FLAC HIRES/MQA audio quality, trying FLAC")
                self._session.audio_quality = tidalapi.Quality.high_lossless
                trackUrl = track.get_url()
        trackCover = track.album.image()
        thread = threading.Thread(target=self._downloadTrackThread, args=(track.full_name, track.album.name, trackCover, [artist.name for artist in track.artists], str(track.tidal_release_date.year), trackUrl.split('.')[-1].split('?')[0] == 'flac', trackUrl))
        thread.start()

    def _downloadTrackThread(self, trackName : str, trackAlbumName : str, trackCoverUrl, trackArtists : list[str], trackReleaseYear : str, isFlac : bool, trackURL : str):
        """
        Download track in a thread to avoid blocking the main thread
        """
        filename = "./tracks/" + re.sub(r'[\\/:*?"<>|]', '-', trackName) + " – " + re.sub(r'[\\/:*?"<>|]', '-', trackArtists[0])
        with urllib.request.urlopen(trackCoverUrl) as f:
            cover_data = f.read()
        if isFlac :
            urllib.request.urlretrieve(trackURL, filename + ".flac")
            audio = FLAC(filename + ".flac")
            cover_picture = Picture()
            cover_picture.data = cover_data
            cover_picture.mime = "image/jpeg"
            cover_picture.type = 3
            audio.add_picture(cover_picture)
            audio["TITLE"] = trackName
            audio["ALBUM"] = trackAlbumName
            audio["ARTIST"] = ", ".join(trackArtists)
            audio["YEAR_OF_RELEASE"] = trackReleaseYear
        else :
            urllib.request.urlretrieve(trackURL, filename + ".m4a")
            audio = MP4(filename + ".m4a")
            audio["covr"] = [bytes(MP4Cover(cover_data, imageformat=MP4Cover.FORMAT_JPEG))]
            audio["\xa9nam"] = trackName
            audio["\xa9alb"] = trackAlbumName
            audio["\xa9ART"] = ", ".join(trackArtists)
            audio["\xa9day"] = trackReleaseYear
        audio.save()

    def _bestTidalSearchResult(self, tracks: list[tidalapi.media.Track], title: str, artists: list[str]) -> tidalapi.media.Track:
        """
        Get the best Tidal search result
        """
        return max(self._rankTidalSearchResults(tracks, title, artists), key=lambda x:x["score"])["track"]

    def _rankTidalSearchResults(self, tracks: list[tidalapi.media.Track], title: str, artists: list[str]) -> list[dict]:
        """
        Rank Tidal search results with a score
        """
        rankList = []
        for track in tracks :
            rankList.append({"score" : 0, "track": track})
            if artists != ["<No artist provided>"] and len(track.artists) != 0 :
                trackArtists = [artist.name for artist in track.artists]
                rankList[-1]["score"] += self._rateOfCommonElements(artists, trackArtists)
            rankList[-1]["score"] += self._rateOfCommonCharacters(title, track.full_name)
        return rankList

    def _rateOfCommonCharacters(self, string1: str, string2: str) -> float:
        """
        Get the rate of common characters between two strings
        """
        count = 0
        if len(string1)<len(string2):
            for i in range(len(string1)):
                if string1[i] == string2[i]:
                    count += 1
            return count/len(string2)
        else:
            for i in range(len(string2)):
                if string1[i] == string2[i]:
                    count += 1
            return count/len(string1)

    def _rateOfCommonElements(self, list1: list, list2: list) -> float:
        """
        Get the rate of common elements between two lists
        """
        count = 0
        if len(list1)<len(list2):
            for element in list1:
                if element in list2:
                    count += 1
            return count/len(list2)
        else:
            for element in list2:
                if element in list1:
                    count += 1
            return count/len(list1)

    def _getFavorites(self) -> tidalapi.user.Favorites:
        """
        Search track and add it to favorites if found
        """
        print("📂 Obtaining Tidal favorites tracks.")
        return tidalapi.Favorites(self._session, self._session.user.id)


class YTMusicManager(ytm2tidal):
    def __init__(self, oauthFile: str):
        self._ytm = ytmusicapi(oauthFile, oauth_credentials=OAuthCredentials(client_id=os.getenv('CLIENT_ID'), client_secret=os.getenv('CLIENT_SECRET')))
        self._likedTracksLimit = self._askForLikedTracksLimit()
        self._likedTracks = self._getLikedTracks()

    @property
    def likedTracks(self):
        return self._likedTracks

    @property
    def likedTracksLimit(self):
        return self._likedTracksLimit

    def _getLikedTracks(self) -> dict:
        """
        Obtain YTMusic liked songs with API
        """
        print("📂 Obtaining YTMusic liked tracks.")
        return self._ytm.get_liked_songs(self._likedTracksLimit)

    def _askForLikedTracksLimit(self) -> int:
        """
        Ask user for liked tracks limit
        """
        try:
            self._likedTracksLimit = int(
                input("❓ How many tracks do you want to process ?\n"))
            assert 1 <= self._likedTracksLimit
            return self._likedTracksLimit
        except (ValueError, AssertionError):
            print("⚠️ Input must be an integer greater than 1.")
            return self._askForLikedTracksLimit()


if __name__ == "__main__":
    ytm2tidal()
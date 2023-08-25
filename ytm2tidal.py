import re
import tidalapi
from ytmusicapi import YTMusic as ytmusicapi

""" Multiprocessing is useless because its excessive speed generates 
a 429 error on Tidal servers (Too Many Requests for url). """
# import multiprocess as mp


class ytm2tidal:
    def __init__(self):
        self._tidal = TidalManager()
        self._ytmusic = YTMusicManager("oauth.json")
        self._successCounter, self._failureCounter = 0, 0
        self._processAllTracks()

    def _tryProcessTrack(self, title: str, artist: str = None) -> bool:
        """
        Try to search and add a track to favorites
        """
        if self._tidal.searchAndAddTrackToFavorites(title, artist):
            return True
        cleanTitle = re.sub("[\(\[].*?[\)\]]", "", title)
        if cleanTitle != title:
            print(
                "⚠ Nothing found. Trying again without parentheses and brackets in title.")
            if self._tidal.searchAndAddTrackToFavorites(cleanTitle, artist):
                return True
        return False

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
                if self._tryProcessTrack(ytmTrackInfo["title"], ytmTrackArtist):
                    self._successCounter += 1
                    print("✅ Successfully processed track.")
                    return True
        print("🏷 Trying without any artist name")
        if self._tryProcessTrack(ytmTrackInfo["title"]):
            self._successCounter += 1
            print("✅ Successfully processed track.")
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

        for likedTrack in ytmLikedTracks:
            self._processTrack(likedTrack)
        print("---------\n---------\n📋 Processed " + str(self._successCounter + self._failureCounter) +
              " tracks. (" + str(self._successCounter) + " succeeded / " + str(self._failureCounter) + " failed)")


class TidalManager(ytm2tidal):
    def __init__(self):
        self._session = tidalapi.Session()
        self._session.login_oauth_simple()
        self._favorites = self._getFavorites()

    def _searchTrack(self, query: str) -> tidalapi.media.Track | None:
        """
        Search track on Tidal with API
        """
        print("🔎 Searching track on Tidal (Query : " + query + ")")
        return self._session.search(query, [tidalapi.media.Track])["top_hit"]

    def _addTrackToFavorites(self, track: tidalapi.media.Track) -> None:
        """
        Add a track to favorites on Tidal with API
        """
        print("➕ Track found on Tidal. Addding '" + track.name +
              "' by '" + track.artists[0].name + "' to favorites on Tidal")
        self._favorites.add_track(track.id)

    def searchAndAddTrackToFavorites(self, title: str, artist: str = None) -> bool:
        """
        Search track and add it to favorites if found
        """
        tidalTrack = self._searchTrack(
            title if artist is None else title + " " + artist)
        if tidalTrack != None:
            self._addTrackToFavorites(tidalTrack)
            return True
        return False

    def _getFavorites(self) -> tidalapi.user.Favorites:
        """
        Search track and add it to favorites if found
        """
        print("📂 Obtaining Tidal favorites tracks")
        return tidalapi.Favorites(self._session, self._session.user.id)


class YTMusicManager(ytm2tidal):
    def __init__(self, oauthFile: str):
        self._ytm = ytmusicapi(oauthFile)
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
        print("📂 Obtaining YTMusic liked tracks")
        return self._ytm.get_liked_songs(self._likedTracksLimit)

    def _askForLikedTracksLimit(self) -> int:
        """
        Ask user for liked tracks limit
        """
        try:
            self._likedTracksLimit = int(
                input("How many tracks do you want to process ?\n"))
            assert 1 <= self._likedTracksLimit
            return self._likedTracksLimit
        except (ValueError, AssertionError):
            print("Input must be an integer greater than 1.")
            return self._askForLikedTracksLimit()


if __name__ == "__main__":
    ytm2tidal()

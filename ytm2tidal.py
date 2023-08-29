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

    def _tryProcessTrack(self, title: str, artists: list[str], artist: str = None) -> int:
        """
        Try to search and add a track to favorites
        """
        response = self._tidal.searchAndAddTrackToFavorites(title, artists, artist)
        if response == 1 or response == 2 :
            return response
        cleanTitle = re.sub("[\(\[].*?[\)\]]", "", title)
        if cleanTitle != title:
            print(
                "⚠ Nothing found. Trying again without parentheses and brackets in title.")
            response = self._tidal.searchAndAddTrackToFavorites(cleanTitle, artists, artist)
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
                print("🆗 Track is already in Tidal favorites")
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
        return self._session.search(query, [tidalapi.media.Track])

    def _addTrackToFavorites(self, track: tidalapi.media.Track) -> None:
        """
        Add a track to favorites on Tidal with API
        """
        print("➕ Track found on Tidal. Addding '" + track.name +
              "' by '" + track.artists[0].name + "' to favorites on Tidal")
        self._favorites.add_track(track.id)

    def searchAndAddTrackToFavorites(self, title: str, artists : list[str], artist: str = None) -> int:
        """
        Search track and add it to favorites if found
        """
        tidalSearch = self._searchTrack(
            title if artist is None else title + " " + artist)
        tidalTrackList = tidalSearch["tracks"]
        if len(tidalTrackList) != 0 :
            bestTrack = self._bestTidalSearchResult(tidalTrackList, title, artists)
            if bestTrack.id not in [track.id for track in self._favorites.tracks()] :
                self._addTrackToFavorites(bestTrack)
                return 1
            else :
                return 2
        return 0

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

    def _rateOfCommonElements(self, list1: str, list2: str) -> float:
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
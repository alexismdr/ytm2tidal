import re
import tidalapi
from ytmusicapi import YTMusic

def searchTidalTrack(query: str) -> tidalapi.media.Track | None:
    """
    Search track on Tidal with API
    """
    print("🔎 Searching track on Tidal (Query : " + query + ")")
    return session.search(query, [tidalapi.media.Track])["top_hit"]

def getYTMusicLikedTracks() -> dict:
    """
    Obtain YTMusic liked songs with API
    """
    print("📂 Obtaining YTMusic liked songs")
    return ytm.get_liked_songs(ytmLikedTracksLimit)

def addTrackToTidalFavorites(track: tidalapi.media.Track) -> None:
    """
    Add a track to favorites on Tidal with API
    """
    print("➕ Track found on Tidal. Addding '" + track.name + "' by '" + track.artists[0].name + "' to favorites on Tidal")
    tidalFavorites.add_track(track.id)

def searchAndAddTrackToTidalFavorites(title : str, artist : str=None) -> bool:
    """
    Search track and add it to favorites if found
    """
    tidalTrack = searchTidalTrack(title if artist is None else title + " " + artist)
    if tidalTrack != None :
        addTrackToTidalFavorites(tidalTrack)
        return True
    return False

def askForYTMusicLikedTracksLimit() -> int:
    """
    Ask user for liked tracks limit
    """
    try: 
        ytmLikedTracksLimit = int(input("How many tracks do you want to process ?\n"))
        assert 1 <= ytmLikedTracksLimit
        return ytmLikedTracksLimit
    except (ValueError, AssertionError):
        print("Input must be an integer greater than 1.")
        return askForYTMusicLikedTracksLimit()


def tryProcessTrack(title : str, artist : str=None) -> bool:
    """
    Try to search and add a track to favorites
    """
    if searchAndAddTrackToTidalFavorites(title,artist):
        return True
    cleanTitle = re.sub("[\(\[].*?[\)\]]", "", title)
    if cleanTitle != title :
        print("⚠ Nothing found. Trying again without parentheses and brackets in title.")
        if searchAndAddTrackToTidalFavorites(cleanTitle,artist):
            return True
    return False

def processTrack(ytmTrackInfo: dict) -> bool:
    """
    Process track
    """
    ytmTrackArtists = [artist["name"] for artist in ytmTrackInfo["artists"]] if ytmTrackInfo["artists"] != None else ["<No artist provided>"]
    print("---\n⏳ Processing '" + ytmTrackInfo["title"] + "' by '" + ', '.join(ytmTrackArtists) + "' (from YTMusic)")
    if ytmTrackArtists[0] != "<No artist provided>":
        for ytmTrackArtist in ytmTrackArtists:
            print("🏷 Trying with '" + ytmTrackArtist + "' artist name.")
            if tryProcessTrack(ytmTrackInfo["title"], ytmTrackArtist) :
                return True
    print("🏷 Trying without any artist name")
    if tryProcessTrack(ytmTrackInfo["title"]) :
        return True
    return False

def processAllTracks() :
    """
    Process all tracks
    """
    successCounter, failureCounter = 0, 0
    for i in range(min(len(ytmLikedTracks["tracks"]),ytmLikedTracksLimit)):
        if processTrack(ytmLikedTracks["tracks"][i]) :
            successCounter += 1
            print("✅ Successfully processed track.")
        else :
            failureCounter += 1
            print("❌ Found nothing. Skipping track.")
    print("---------\n---------\n📋 Processed " + str(successCounter + failureCounter) + " tracks. (" + str(successCounter) + " succeeded / " + str(failureCounter) + " failed)")

def main() :
    """
    Main function
    """
    global ytm, session, ytmLikedTracks, tidalFavorites, ytmLikedTracksLimit
    ytm = YTMusic("oauth.json")
    session = tidalapi.Session()
    session.login_oauth_simple()
    ytmLikedTracksLimit = askForYTMusicLikedTracksLimit()
    ytmLikedTracks = getYTMusicLikedTracks()
    tidalFavorites = tidalapi.Favorites(session, session.user.id)
    processAllTracks()

main()






import re
import tidalapi
from ytmusicapi import YTMusic

# YTMusic OAuth Login
ytm = YTMusic("oauth.json")

# Tidal OAuth Login
session = tidalapi.Session()
session.login_oauth_simple()

# Get favorites playlists on both YTMusic and Tidal
ytmLikedSongs = ytm.get_liked_songs(10000)
favorites = tidalapi.Favorites(session, session.user.id)

def searchTidalTrack(query: str):
    print("🔎 Searching track on Tidal (Query : " + query + ")")
    return session.search(query, [tidalapi.media.Track])["top_hit"]

def addTrackToFavorites(track):
    print("➕ Track found on Tidal. Addding '" + track.name + "' by '" + track.artists[0].name + "' to favorites on Tidal")
    favorites.add_track(track.id)

successCounter = 0
failureCounter = 0

def processTrack(ytmTrackInfo):
    global successCounter
    global failureCounter
    if ytmTrackInfo["artists"] != None :
        ytmTrackArtists = [ytmTrackInfo["artists"][i]["name"] for i in range(len(ytmTrackInfo["artists"]))]
    else :
        ytmTrackArtists = ["<No artist provided>"]
    print("---\n⏳ Processing '" + ytmTrackInfo["title"] + "' by '" + ', '.join(ytmTrackArtists) + "' (from YTMusic)")
    if ytmTrackArtists[0] != "<No artist provided>":
        for ytmTrackArtist in ytmTrackArtists:
            print("🏷 Trying with '" + ytmTrackArtist + "' artist name.")
            tidalTrack = searchTidalTrack(ytmTrackInfo["title"] + " " + ytmTrackArtist)
            if tidalTrack != None :
                addTrackToFavorites(tidalTrack)
                successCounter += 1
                return "✅ Successfully processed track."
            else :
                print("⚠ Found nothing. Trying again without parentheses and brackets in title.")
                tidalTrack = searchTidalTrack(re.sub("[\(\[].*?[\)\]]", "", ytmTrackInfo["title"]) + " " + ytmTrackArtist)
                if tidalTrack != None :
                    addTrackToFavorites(tidalTrack)
                    successCounter += 1
                    return "✅ Successfully processed track."
    print("🏷 Trying without any artist name")
    tidalTrack = searchTidalTrack(ytmTrackInfo["title"])
    if tidalTrack != None :
        addTrackToFavorites(tidalTrack)
        successCounter += 1
        return "✅ Successfully processed track."
    else :
        print("⚠ Found nothing. Trying again without parentheses and brackets in title.")
        tidalTrack = searchTidalTrack(re.sub("[\(\[].*?[\)\]]", "", ytmTrackInfo["title"]))
        if tidalTrack != None :
            addTrackToFavorites(tidalTrack)
            successCounter += 1
            return "✅ Successfully processed track."
        else :
            failureCounter += 1
            return "❌ Found nothing. Skipping track."


# Process transfer
for i in range(len(ytmLikedSongs["tracks"])):
    print(processTrack(ytmLikedSongs["tracks"][i]))

# Print summary
print("---------\n---------\n📋 Processed " + str(successCounter + failureCounter) + " tracks. (" + str(successCounter) + " succeeded / " + str(failureCounter) + " failed)")




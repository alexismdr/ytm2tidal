# ➡ YouTube Music to Tidal *(ytm2tidal)*
## Why
I only use Tidal to stream to particular devices (Hi-Fi audio systems, rekordbox,...) and YT Music as a daily driver on which I keep my playlist up to date. So I wanted a simple, free, fast and self-hosted way to transfer my playlist from YT Music to Tidal.
## Solution
### How
A simple, short python program performs this task. It transfers all the tracks in the "Likes" playlist on YT Music to the favorites on Tidal.
### Requirements
- Python 3.11+
- Pip 23.1.2+
### Steps
*Commands are given as examples for Linux with Python 3.11*
1. Open a shell
2. Clone this repository : `git clone https://github.com/alexismdr/ytm2tidal`
3. Go to the folder : `cd ytm2tidal`
4. Create virtual environment : `python -m venv .venv`
5. Enable virtual environment : `source .venv/bin/activate`
6. Install requirements : `pip install -r requirements.txt`
7. Create a Google Cloud Console Project with YouTube Data API enabled, obtain your OAuth credentials (client_id and client_secret), put them in the `.env.example` file and rename it to `.env`.
8. Setup YouTube OAuth : `ytmusicapi oauth` (follow the instructions) using your OAuth credentials.
9. Launch program : `python3.11 ytm2tidal.py`
10. Follow the instructions to login to Tidal
11. Enter the limit for the number of tracks to be processed
12. Enjoy 😁
## Additional information
I've posted this repository publicly because I'm thinking of improving this program in the future (e.g. choosing playlists, performing the reverse operation, adding more music platforms, creating a web interface, hosting the service myself for everyone, not using libraries, recoding the program in another language, etc.). For the time being, it will remain a very simple program, as I don't have the time to devote to such a project.



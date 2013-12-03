#Bittorrent Client
------
A BitTorrent client written in Python using Twisted. I found the [unofficial spec](https://wiki.theory.org/BitTorrentSpecification) and this [blog post](http://www.kristenwidman.com/blog/how-to-write-a-bittorrent-client-part-1/) incredibly useful. Official spec is [here](http://bittorrent.org/beps/bep_0003.html).

###How to use
* `pip install -r requirements.txt`
* `python bt.py path/to/torrent.torrent`

###What works
* Creation of all messages
* Parsing and processing of incoming bitfield, have, piece, choke, unchoke, interested, and not-interested messages.
* Downloading a single file from multiple peers.

###What doesn't (yet)
* Processing incoming request messages and sending piece responses (seeding).
* Error handling of bad data or malicious peers.
* Multiple file downloads.
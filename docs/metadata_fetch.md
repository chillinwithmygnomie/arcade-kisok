Metadata & Box Art fetching

This feature lets the generate_gamelists script query TheGamesDB to retrieve
basic metadata (title, overview, release date, publisher) and box art for
ROMs. Box art images are saved into /home/kiosk/roms/<system>/images/.

How to get an API key
1. Register at TheGamesDB: https://thegamesdb.net/
2. Create an API key on your account dashboard (the service provides free keys for personal use).
3. On the kiosk machine, create the config directory and a config file:

   sudo -u kiosk mkdir -p /home/kiosk/.config/arcade-kiosk
   sudo -u kiosk tee /home/kiosk/.config/arcade-kiosk/metadata.json > /dev/null <<EOF
   {"provider":"thegamesdb","api_key":"YOUR_KEY_HERE","fetch_on_boot":false}
   EOF
   sudo chmod 600 /home/kiosk/.config/arcade-kiosk/metadata.json

Configuration options
- provider: currently only "thegamesdb" is supported
- api_key: your API key for the provider
- fetch_on_boot: if true, generate_gamelists will fetch metadata when run without --fetch-art
- sleep_between_requests: seconds to wait between API calls (respect rate limits)

How to run metadata fetch manually
- Run the dedicated systemd unit (recommended):
    sudo systemctl start generate-gamelists-fetch.service

- Or run the script directly as kiosk:
    sudo -u kiosk /home/kiosk/tools/generate_gamelists.py --romdir /home/kiosk/roms --merge --fetch-art

Notes & limitations
- Matching from ROM filename to database entry is heuristic; some matches may be incorrect or missing.
- TheGamesDB API structure can change; the script attempts to be resilient but may need tweaks over time.
- Respect copyright: only fetch artwork/metadata for ROMs you legally own.

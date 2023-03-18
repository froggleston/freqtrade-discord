# freqtrade-discord

Unofficial discord bot to view and control running freqtrade instances.

At the moment, only `$servers`, `$ping` and `$status` commands work!

## Requirements

Run `pip3 install -r requirements.txt` to install dependencies.

## Installation and Setup

### Installing the python script

* Put the `ft_bot.py` and `example.yaml` files wherever the FT bot is running 
  * The easiest place would be the freqtrade/scripts folder
  * Yes, you can view and control multiple bots!

* Rename/copy the `example.yaml` file as a new file, e.g. `my_ft_bots.yaml`, and edit this new file:
  * Leave the `token` field at the top of the file empty for now
  * Set a unique simple name for each freqtrade bot instance
  * Set the IP and port information for each freqtrade bot you want to add
    * e.g. if you have a single bot running on localhost:8080, add in localhost as the IP and 8080 as the port
  * Set the username and password information
  * Save the file

### Creating the bot in the Discord Developer Portal

* Create a [Discord Developer Portal](https://discord.com/developers) account

* Register a New Application as per the [discord.py docs](https://discordpy.readthedocs.io/en/latest/discord.html)
  * Log in to the Discord Developer Portal
  * Click `New Application`
  * Give the bot a name, like `ft_bot`
  
* Click on `Bot` in the left-hand navigation menu, then `Add Bot`

  * Add a profile picture if you want an easier way to identify your bot in your discord server

  * Under `Token`:
    * Click `Copy`
    * Go to your `my_ft_bots.yaml` file, and paste this token in to the `token` string field
    * Save your yaml file
    * __Do NOT share the bot token with anyone else - it is your bot password__
    * You can copy this token only once. If you forget it or do not copy it now, you will need to click `Reset Token` and replace the token in your yaml file with the new one

  * Go back to the Developer Portal

  * Under `Authorization Flow`:
    * __Public Bot__ should be UNCHECKED
    * __Requires OAuth2 code grant__ should be UNCHECKED

  * Under `Privileged Gateway Intents`:
    * __Presence Intent__ should be UNCHECKED
    * __Server Members Intent__ should be UNCHECKED
    * __Message Content Intent__ should be CHECKED

  * Click `Save Changes`

* Click the `OAuth2` in the left-hand navigation menu, then `URL Generator` 
  * Under `Scopes`:
    * Click `bot`

  * Under `Bot Permissions`:
    * __Send Messages__ should be CHECKED
    * __Read Messages/View Channels__ should be CHECKED
    * __Read Message History__ should be CHECKED
  
  * Copy the `Generated URL` at the bottom of the page

* Open the Generated URL in a browser
  * Check that you're signed in as the correct user for your chosen discord server
  * Select the server you wish to add the bot to in `Add to server`
  * Confirm that the bot is set to Read Messages and Send Messages
  * Close the tab

### Running the ft_bot.py script

* Run the `ft_bot.py` script in a [screen](https://www.redhat.com/sysadmin/tips-using-screen) or [tmux](https://www.redhat.com/sysadmin/introduction-tmux-linux)
  * `python3 ft_bot.py -y my_ft_bots.yaml`

### Checking the bot is in your discord server

* Go to your discord server, Server Settings, and Integrations
  * Your new bot should be listed under `Bots and Apps` - congratulations!
  * Click on `Manage` next to your bot, and select the channels you wish this bot to listen on, and who you wish to be able to message the bot
  * Consider setting strict user access, e.g. you only, so that you can restrict who can control the bot as the bot matures and gets more commands

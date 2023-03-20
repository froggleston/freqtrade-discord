#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
freqtrade-discord
An unofficial discord bot to view and control freqtrade bots, much like
the telegram implementation.

NB: This discord bot requires the 'message_content' intent to be set
in the Discord Developer portal for this app.

Licence: MIT [https://github.com/froggleston/freqtrade-frogtrade9000/blob/main/LICENSE]

Donations:
    BTC: bc1qxdfju58lgrxscrcfgntfufx5j7xqxpdufwm9pv
    ETH: 0x581365Cff1285164E6803C4De37C37BbEaF9E5Bb

Conception Date: 2023-03-17

"""

import aiohttp
import argparse
import discord
import logging
import traceback
from typing import Any, Dict, List, Optional

from tabulate import tabulate

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("ft_bot")

class ft_bot(discord.Client):

    def __init__(self,
                 intents: discord.Intents, 
                 servers: Dict,
                 disabled_calls: Optional[List[str]] = None):
        self.servers = {}
        self.available_calls = {'ping' : self._process_ping,
                                'status' : self._process_status}

        logger.info(f"Available commands: {list(self.available_calls.keys())}")

        if disabled_calls is not None:
            self.disabled_calls = disabled_calls
            logger.info(f"Disabled commands: {self.disabled_calls}")

        for s in servers:
            server = {}
            server['ip'] = s['ip']
            server['port'] = s['port']
            server['auth'] = aiohttp.BasicAuth(login=s['username'],
                                               password=s['password'],
                                               encoding='utf-8')
            self.servers[s['name']] = server
        
        super().__init__(intents=intents)

    def _on_ready(self):
        print(f'We have logged in as {self.user}. Tracking {len(servers)} freqtrade servers')

    async def process_command(self, 
                              server: str,
                              command: str,
                              command_args: Optional[List[Any]]) -> Dict:
        ip = self.servers[server]['ip']
        port = self.servers[server]['port']
        auth = self.servers[server]['auth']
        base_url = f"http://{ip}:{port}/api/v1"

        cmd = command.replace("$","")

        if cmd in self.available_calls and cmd not in self.disabled_calls:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{base_url}/{cmd}') as r:
                    if r.status == 200:
                        js = await r.json()
                        return self.available_calls[cmd](js, command_args)
                    else:
                        raise Exception(f"Error: Status {r.status} received.")
        else:
            raise Exception(f"Function '{cmd}' not available or is disabled by the server admin.")
        
        return None

    def _process_ping(self, data: Dict, command_args = None):
        embeds = [
            {"title":"PING",
            "fields":[{"name":"Response","value":data['status']}]
            }
        ]
        embed = discord.Embed.from_dict(embeds[0])
        return embed

    def _process_status(self, data: Dict, command_args = None):
        msg = []
        headers = ["ID","PAIR","PROFIT %","PROFIT"]
        msg.append(headers)
        for trade in data:
            msg.append(
                [trade['trade_id'],
                trade['pair'],
                trade['current_profit_pct'],
                f"{trade['current_profit_abs']} {trade['quote_currency']}"
                ]
            )
        table = tabulate(msg, headers='firstrow', tablefmt='grid')
        embed = f"```{table}```"
        return embed

    # def send_msg(self, server: str, msg: Dict, title: str) -> Dict:
    #     msg['bot'] = server
    #     color = 0x0000FF
    #     if msg['type'] in (RPCMessageType.EXIT, RPCMessageType.EXIT_FILL):
    #         profit_ratio = msg.get('profit_ratio')
    #         color = (0x00FF00 if profit_ratio > 0 else 0xFF0000)
    #     if 'pair' in msg:
    #         title = f"Trade: {msg['pair']} {msg['type'].value}"
    #     embeds = [{
    #         'title': title,
    #         'color': color,
    #         'fields': [],
    #     }]
    #     for f in fields:
    #         for k, v in f.items():
    #             v = v.format(**msg)
    #             embeds[0]['fields'].append(
    #                 {'name': k, 'value': v, 'inline': True})

    #     # Send the message to discord channel
    #     payload = {'embeds': embeds}
    #     return payload

    async def on_message(self, message) -> None:
        # don't let the bot reply to itself
        if message.author == self.user:
            return

        cmd_string = message.content.split(" ")
        cmd = cmd_string[0]

        if cmd.startswith('$servers'):
            resp = []
            headers = ["NAME","IP","PORT"]
            resp.append(headers)

            for k,v in self.servers.items():
                resp.append([k,v['ip'],v['port']])
            table = tabulate(resp,headers='firstrow',tablefmt='grid')
            await message.channel.send(f"```{table}```")
        else:
            cmd_args = []

            if len(self.servers) == 1:
                server = list(self.servers.keys())[0]
                cmd_args = cmd_string[1:]
            else:
                if len(cmd_string) > 1:
                    server = cmd_string[1]
                    cmd_args = cmd_string[2:]
                else:
                    await message.channel.send("ERROR: No server specified. Run `$servers` to list them.")

                try:
                    embed = self.process_command(server, cmd, cmd_args)
                    if embed is not None:
                        await message.channel.send(embed=embed)
                except Exception as e:
                    await message.channel.send(f"ERROR: {e}")


class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def add_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("-y", "--yaml", nargs='?', help="Supply a YAML file.")
    args = parser.parse_args()
    
    return args

def main(args):
    if args.yaml is not None:
        import yaml
        with open(args.yaml, 'r') as yamlfile:
            args = dotdict(yaml.safe_load(yamlfile))
            args.yaml = True

    if args.yaml:
        if not args.token or args.token == "":
            raise Exception("No discord token supplied.")

        if len(args.servers) == 0:
            raise Exception("No freqtrade servers supplied.")

        intents = discord.Intents.default()
        intents.message_content = True

        try:
            if args.disabled_calls and len(args.disabled_calls) > 0:
                client = ft_bot(intents=intents,
                                servers=args.servers,
                                disabled_calls=args.disabled_calls)
            else:
                client = ft_bot(intents=intents,
                                servers=args.servers)
                                
            client.run(args.token)
        except Exception as e:
            logger.error(f"Cannot start ft_bot: ", e)
    else:
        raise Exception("No YAML file supplied.")

if __name__ == "__main__":
    args = add_arguments()

    try:
        main(args)

    except Exception as e:
        traceback.print_exc()
        logger.error("You got frogged: ", e)

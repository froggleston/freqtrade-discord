#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
freqtrade-discord
An unofficial discord bot to view and control freqtrade bots, much like
the telegram implementation.

NB: This discord bot requires the 'message_content' intent to be set
in the Discord Developer portal for this app.

Docs: [https://github.com/froggleston/freqtrade-discord/blob/main/README.md]
Licence: MIT [https://github.com/froggleston/freqtrade-discord/blob/main/LICENSE]

Donations:
    BTC: bc1qxdfju58lgrxscrcfgntfufx5j7xqxpdufwm9pv
    ETH: 0x581365Cff1285164E6803C4De37C37BbEaF9E5Bb

Conception Date: 2023-03-17

"""

import aiohttp
import argparse
import arrow
import discord
import json
import logging
import traceback

from dataclasses import dataclass
from discord.embeds import Embed

from tabulate import tabulate
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, urlparse, urlunparse

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("ft_bot")

@dataclass
class TimeunitMappings:
    header: str
    message: str
    message2: str
    callback: str
    default: int

CMD_PREFIX_CHAR = "/"

class ft_bot(discord.Client):

    def __init__(self,
                 intents: discord.Intents,
                 servers: dict,
                 disabled_calls: Optional[List[str]] = None):
        self.servers = {}
        self.available_calls = {'ping' : self._process_ping,
                                'show_config' : self._process_show_config,
                                'status' : self._process_status,
                                'profit' : self._process_profit,
                                'trades' : self._process_trades,
                                'daily' : self._process_daily,
                                'weekly' : self._process_weekly,
                                'monthly' : self._process_monthly,}

        logger.info(f"Available commands: {list(self.available_calls.keys())}")

        self.disabled_calls = []
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
        logger.info(f'We have logged in as {self.user}. Tracking {len(self.servers)} freqtrade servers')

    async def process_command(self,
                              server: str,
                              command: str,
                              params: dict = {}) -> dict:
        ip = self.servers[server]['ip']
        port = self.servers[server]['port']
        auth = self.servers[server]['auth']
        base_url = f"http://{ip}:{port}/api/v1"

        if 'config' not in self.servers[server]:
            logger.info(f"No config for {server} found - getting...")
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{base_url}/show_config', auth=auth) as r:
                    if r.status == 200:
                        self.servers[server]['config'] = await r.json()

        cmd = command.replace(CMD_PREFIX_CHAR,"")

        if cmd in self.available_calls and cmd not in self.disabled_calls:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{base_url}/{cmd}", params=params, auth=auth) as r:
                    if r.status == 200:
                        js = await r.json()
                        return js
                    else:
                        raise Exception(f"Error: Status {r.status} received.")
        else:
            raise Exception(f"Function '{cmd}' not available or is disabled by the server admin.")

    def _process_ping(self, server, data, *command_args):
        """
        */ping <server>* : Ping the bot
        """
        embeds = [
            {
                "title":f"PING {server}",
                "fields":[
                    {"name":"Response","value":data['status']},
                ]
            }
        ]
        embed = discord.Embed.from_dict(embeds[0])
        return embed

    def _process_profit(self, server, data, *command_args):
        """
        */profit <server>* : Get profit summary for a bot
        """

        markdown_msg = f"**{server} - Profit Summary**\n"

        stake_cur = self.servers[server]['config']['stake_currency']
        # fiat_disp_cur = self.servers[server]['config'].get('fiat_display_currency', '') # TODO FIX RPC Profit model

        profit_closed_coin = data['profit_closed_coin']
        profit_closed_ratio_mean = data['profit_closed_ratio_mean']
        profit_closed_percent = data['profit_closed_percent']
        profit_closed_fiat = data['profit_closed_fiat']
        profit_all_coin = data['profit_all_coin']
        profit_all_ratio_mean = data['profit_all_ratio_mean']
        profit_all_percent = data['profit_all_percent']
        profit_all_fiat = data['profit_all_fiat']
        trade_count = data['trade_count']
        first_trade_date = f"{data['first_trade_humanized']} ({data['first_trade_date']})"
        latest_trade_date = f"{data['latest_trade_humanized']} ({data['latest_trade_date']})"
        avg_duration = data['avg_duration']
        best_pair = data['best_pair']
        best_pair_profit_ratio = data['best_pair_profit_ratio']
        winrate = data['winrate']
        expectancy = data['expectancy']
        expectancy_ratio = data['expectancy_ratio']

        if data['trade_count'] == 0:
            markdown_msg += f"No trades yet.\n*Bot started:* `{data['bot_start_date']}`"
        else:
            if data['closed_trade_count'] > 0:
                markdown_msg += ("*ROI:* Closed trades\n"
                                f"∙ `{round_coin_value(profit_closed_coin, stake_cur)} "
                                f"({profit_closed_ratio_mean:.2%}) "
                                f"({profit_closed_percent} \N{GREEK CAPITAL LETTER SIGMA}%)`\n")
                                # f"∙ `{round_coin_value(profit_closed_fiat, fiat_disp_cur)}`\n")
            else:
                markdown_msg += "`No closed trade` \n"

            markdown_msg += (
                f"*ROI:* All trades\n"
                f"∙ `{round_coin_value(profit_all_coin, stake_cur)} "
                f"({profit_all_ratio_mean:.2%}) "
                f"({profit_all_percent} \N{GREEK CAPITAL LETTER SIGMA}%)`\n"
                # f"∙ `{round_coin_value(profit_all_fiat, fiat_disp_cur)}`\n"
                f"*Total Trade Count:* `{trade_count}`\n"
                f"*Bot started:* `{data['bot_start_date']}`\n"
                f"*First Trade opened:* `{first_trade_date}`\n"
                f"*Latest Trade opened:* `{latest_trade_date}`\n"
                f"*Win / Loss:* `{data['winning_trades']} / {data['losing_trades']}`\n"
                f"*Winrate:* `{winrate:.2%}`\n"
                f"*Expectancy (Ratio):* `{expectancy:.2f} ({expectancy_ratio:.2f})`"
            )
            if data['closed_trade_count'] > 0:
                markdown_msg += (
                    f"\n*Avg. Duration:* `{avg_duration}`\n"
                    f"*Best Performing:* `{best_pair}: {best_pair_profit_ratio:.2%}`\n"
                    f"*Trading volume:* `{round_coin_value(data['trading_volume'], stake_cur)}`\n"
                    f"*Profit factor:* `{data['profit_factor']:.2f}`\n"
                    f"*Max Drawdown:* `{data['max_drawdown']:.2%} "
                    f"({round_coin_value(data['max_drawdown_abs'], stake_cur)})`\n"
                    f"    from `{data['max_drawdown_start']}` \n"
                    #f"({round_coin_value(data['drawdown_high'], stake_cur)})`\n" # TODO FIX RPC Profit model
                    f"    to `{data['max_drawdown_end']}` \n"
                    #f"({round_coin_value(data['drawdown_low'], stake_cur)})`\n"
                )

        return discord.Embed(description=markdown_msg)

    def _process_status(self, server, data, *command_args):
        """
        */status <server>* : Show the status of a bot
        """
        if data and len(data) > 0:
            if len(command_args) == 0:
                msg = []
                headers = ["ID","PAIR","PROFIT %","PROFIT"]
                msg.append(headers)

                for trade in data:
                    msg.append(
                        [trade['trade_id'],
                        trade['pair'],
                        trade['total_profit_ratio']*100,
                        f"{trade['total_profit_abs']} {trade['quote_currency']}"
                        ]
                    )
                table = tabulate(msg, headers='firstrow', tablefmt='grid')
                return f"```{table}```"
            # else:
            #     embeds = []
            #     position_adjust = self.servers[server]['position_adjustment_enable']
            #     for r in data:
            #         msg = ""

            #         r['open_date_hum'] = arrow.get(r['open_date']).humanize()
            #         r['num_entries'] = len([o for o in r['orders'] if o['ft_is_entry']])
            #         r['num_exits'] = len([o for o in r['orders'] if not o['ft_is_entry']
            #                             and not o['ft_order_side'] == 'stoploss'])
            #         r['exit_reason'] = r.get('exit_reason', "")
            #         r['stake_amount_r'] = round_coin_value(r['stake_amount'],
            #                                                r['quote_currency'])
            #         r['max_stake_amount_r'] = round_coin_value(
            #             r['max_stake_amount'] or r['stake_amount'], r['quote_currency'])
            #         r['profit_abs_r'] = round_coin_value(r['profit_abs'],
            #                                              r['quote_currency'])
            #         r['realized_profit_r'] = round_coin_value(r['realized_profit'],
            #                                                   r['quote_currency'])
            #         r['total_profit_abs_r'] = round_coin_value(
            #             r['total_profit_abs'], r['quote_currency'])
            #         lines = [
            #             "*Trade ID:* `{trade_id}`" +
            #             (" `(since {open_date_hum})`" if r['is_open'] else ""),
            #             "*Current Pair:* {pair}",
            #             f"*Direction:* {'`Short`' if r.get('is_short') else '`Long`'}"
            #             + " ` ({leverage}x)`" if r.get('leverage') else "",
            #             "*Amount:* `{amount} ({stake_amount_r})`",
            #             "*Total invested:* `{max_stake_amount_r}`" if position_adjust else "",
            #             "*Enter Tag:* `{enter_tag}`" if r['enter_tag'] else "",
            #             "*Exit Reason:* `{exit_reason}`" if r['exit_reason'] else "",
            #         ]

            #         if position_adjust:
            #             max_entries = r['max_entry_position_adjustment']
            #             max_buy_str = (f"/{max_entries + 1}" if (max_entries > 0) else "")
            #             lines.extend([
            #                 "*Number of Entries:* `{num_entries}" + max_buy_str + "`",
            #                 "*Number of Exits:* `{num_exits}`"
            #             ])

            #         lines.extend([
            #             "*Open Rate:* `{open_rate:.8f}`",
            #             "*Close Rate:* `{close_rate:.8f}`" if r['close_rate'] else "",
            #             "*Open Date:* `{open_date}`",
            #             "*Close Date:* `{close_date}`" if r['close_date'] else "",
            #             " \n*Current Rate:* `{current_rate:.8f}`" if r['is_open'] else "",
            #             ("*Unrealized Profit:* " if r['is_open'] else "*Close Profit: *")
            #             + "`{profit_ratio:.2%}` `({profit_abs_r})`",
            #         ])

            #         if r['is_open']:
            #             if r.get('realized_profit'):
            #                 lines.extend([
            #                     "*Realized Profit:* `{realized_profit_ratio:.2%} ({realized_profit_r})`",
            #                     "*Total Profit:* `{total_profit_ratio:.2%} ({total_profit_abs_r})`"
            #                 ])

            #             # Append empty line to improve readability
            #             lines.append(" ")
            #             if (r['stop_loss_abs'] != r['initial_stop_loss_abs']
            #                     and r['initial_stop_loss_ratio'] is not None):
            #                 # Adding initial stoploss only if it is different from stoploss
            #                 lines.append("*Initial Stoploss:* `{initial_stop_loss_abs:.8f}` "
            #                             "`({initial_stop_loss_ratio:.2%})`")

            #             # Adding stoploss and stoploss percentage only if it is not None
            #             lines.append("*Stoploss:* `{stop_loss_abs:.8f}` " +
            #                         ("`({stop_loss_ratio:.2%})`" if r['stop_loss_ratio'] else ""))
            #             lines.append("*Stoploss distance:* `{stoploss_current_dist:.8f}` "
            #                         "`({stoploss_current_dist_ratio:.2%})`")
            #             if r['open_order']:
            #                 lines.append(
            #                     "*Open Order:* `{open_order}`"
            #                     + "- `{exit_order_status}`" if r['exit_order_status'] else "")

            #         lines_detail = self._prepare_order_details(
            #             r['orders'], r['quote_currency'], r['is_open'])
            #         lines.extend(lines_detail if lines_detail else "")

            #         for line in lines:
            #             msg += line + '\n'
            #         embeds.append(msg)
            #     return {'embeds': embeds}
        else:
            return f"`No active trades`"

    # def _prepare_order_details(self, filled_orders: List, quote_currency: str, is_open: bool):
    #     """
    #     Prepare details of trade with entry adjustment enabled
    #     """
    #     lines_detail: List[str] = []
    #     if len(filled_orders) > 0:
    #         first_avg = filled_orders[0]["safe_price"]
    #     order_nr = 0
    #     for order in filled_orders:
    #         lines: List[str] = []
    #         if order['is_open'] is True:
    #             continue
    #         order_nr += 1
    #         wording = 'Entry' if order['ft_is_entry'] else 'Exit'

    #         cur_entry_datetime = arrow.get(order["order_filled_date"])
    #         cur_entry_amount = order["filled"] or order["amount"]
    #         cur_entry_average = order["safe_price"]
    #         lines.append("  ")
    #         if order_nr == 1:
    #             lines.append(f"*{wording} #{order_nr}:*")
    #             lines.append(
    #                 f"*Amount:* {cur_entry_amount} "
    #                 f"({round_coin_value(order['cost'], quote_currency)})"
    #             )
    #             lines.append(f"*Average Price:* {cur_entry_average}")
    #         else:
    #             sum_stake = 0
    #             sum_amount = 0
    #             for y in range(order_nr):
    #                 loc_order = filled_orders[y]
    #                 if loc_order['is_open'] is True:
    #                     # Skip open orders (e.g. stop orders)
    #                     continue
    #                 amount = loc_order["filled"] or loc_order["amount"]
    #                 sum_stake += amount * loc_order["safe_price"]
    #                 sum_amount += amount
    #             prev_avg_price = sum_stake / sum_amount
    #             # TODO: This calculation ignores fees.
    #             price_to_1st_entry = ((cur_entry_average - first_avg) / first_avg)
    #             minus_on_entry = 0
    #             if prev_avg_price:
    #                 minus_on_entry = (cur_entry_average - prev_avg_price) / prev_avg_price

    #             lines.append(f"*{wording} #{order_nr}:* at {minus_on_entry:.2%} avg Profit")
    #             if is_open:
    #                 lines.append("({})".format(cur_entry_datetime
    #                                            .humanize(granularity=["day", "hour", "minute"])))
    #             lines.append(f"*Amount:* {cur_entry_amount} "
    #                          f"({round_coin_value(order['cost'], quote_currency)})")
    #             lines.append(f"*Average {wording} Price:* {cur_entry_average} "
    #                          f"({price_to_1st_entry:.2%} from 1st entry Rate)")
    #             lines.append(f"*Order filled:* {order['order_filled_date']}")

    #         lines_detail.append("\n".join(lines))

    #     return lines_detail

    def _process_trades(self, server: str, data, *command_args):
        """
        */trades <server>* : Show the last 10 trades
        */trades <server> <limit>* : Show the last <limit> trades
        """
        if data and len(data) > 0:
            if len(command_args) == 0:
                num_trades = 10
            else:
                num_trades = command_args[0]

            logger.info(f"{server}: Processing latest {num_trades} trades")
            msg = []
            headers = ["ID","PAIR","CLOSE DATE","PROFIT %","PROFIT"]
            msg.append(headers)

            for trade in data['trades'][-num_trades:]:
                msg.append(
                    [trade['trade_id'],
                    trade['pair'],
                    trade['close_date'],
                    f"{trade['close_profit_pct']} %",
                    f"{trade['profit_abs']} {trade['quote_currency']}"
                    ]
                )
            table = tabulate(msg, headers='firstrow', tablefmt='outline')

            message = (
                f'**{server} - {num_trades} recent trades**:\n'
                f'```{table}```'
            )
            return f"{message}"

        return f"No trades to show"

    def _process_daily(self, server, data, *command_args):
        """
        */daily <server>* : Show the last 12 days profit summary
        */daily <server> <limit>* : Show the last <limit> days profit summary
        """
        num_days = command_args[0] if len(command_args) > 0 else 12

        stats_tab = tabulate(
            [[f"{period['date']} ({period['trade_count']})",
              f"{round_coin_value(period['abs_profit'], data['stake_currency'])}",
              f"{period['fiat_value']:.2f} {data['fiat_display_currency']}",
              f"{period['rel_profit']:.2%}",
              ] for period in data['data']],
            headers=[
                f"Daily (count)",
                f"{data['stake_currency']}",
                f"{data['fiat_display_currency']}",
                'Profit %',
                'Trades',
            ],
            tablefmt='outline')
        message = (
            f'**{server} - Profit over the last {num_days} days**:\n'
            f'```{stats_tab}```'
        )
        return f"{message}"

    def _process_weekly(self, server, data, *command_args):
        """
        */weekly <server>* : Show the last 12 weeks profit summary
        */weekly <server> <limit>* : Show the last <limit> weeks profit summary
        """
        num_weeks = command_args[0] if len(command_args) > 0 else 12

        stats_tab = tabulate(
            [[f"{period['date']} ({period['trade_count']})",
              f"{round_coin_value(period['abs_profit'], data['stake_currency'])}",
              f"{period['fiat_value']:.2f} {data['fiat_display_currency']}",
              f"{period['rel_profit']:.2%}",
              ] for period in data['data']],
            headers=[
                f"Monthly (count)",
                f"{data['stake_currency']}",
                f"{data['fiat_display_currency']}",
                'Profit %',
                'Trades',
            ],
            tablefmt='outline')
        message = (
            f'**{server} - Profit over the last {num_weeks} weeks**:\n'
            f'```{stats_tab}```'
        )
        return f"{message}"

    def _process_monthly(self, server, data, *command_args):
        """
        */monthly <server>* : Show the last 12 months profit summary
        */monthly <server> <limit>* : Show the last <limit> months profit summary
        """
        num_months = command_args[0] if len(command_args) > 0 else 12

        stats_tab = tabulate(
            [[f"{period['date']} ({period['trade_count']})",
              f"{round_coin_value(period['abs_profit'], data['stake_currency'])}",
              f"{period['fiat_value']:.2f} {data['fiat_display_currency']}",
              f"{period['rel_profit']:.2%}",
              ] for period in data['data']],
            headers=[
                f"Monthly (count)",
                f"{data['stake_currency']}",
                f"{data['fiat_display_currency']}",
                'Profit %',
                'Trades',
            ],
            tablefmt='outline')
        message = (
            f'**{server} - Profit over the last {num_months} months**:\n'
            f'```{stats_tab}```'
        )
        return f"{message}"

    def _process_show_config(self, server, data, *command_args):
        """
        */show_config <server>* : Show the config of a bot
        """
        if data['trailing_stop']:
            sl_info = (
                f"*Initial Stoploss:* `{data['stoploss']}`\n"
                f"*Trailing stop positive:* `{data['trailing_stop_positive']}`\n"
                f"*Trailing stop offset:* `{data['trailing_stop_positive_offset']}`\n"
                f"*Only trail above offset:* `{data['trailing_only_offset_is_reached']}`\n"
            )

        else:
            sl_info = f"*Stoploss:* `{data['stoploss']}`\n"

        if data['position_adjustment_enable']:
            pa_info = (
                f"*Position adjustment:* On\n"
                f"*Max enter position adjustment:* `{data['max_entry_position_adjustment']}`\n"
            )
        else:
            pa_info = "*Position adjustment:* Off\n"

        msg = (
            f"*Mode:* `{'Dry-run' if data['dry_run'] else 'Live'}`\n"
            f"*Exchange:* `{data['exchange']}`\n"
            f"*Market: * `{data['trading_mode']}`\n"
            f"*Stake per trade:* `{data['stake_amount']} {data['stake_currency']}`\n"
            f"*Max open Trades:* `{data['max_open_trades']}`\n"
            f"*Minimum ROI:* `{data['minimal_roi']}`\n"
            f"*Entry strategy:* ```\n{json.dumps(data['entry_pricing'])}```\n"
            f"*Exit strategy:* ```\n{json.dumps(data['exit_pricing'])}```\n"
            f"{sl_info}"
            f"{pa_info}"
            f"*Timeframe:* `{data['timeframe']}`\n"
            f"*Strategy:* `{data['strategy']}`\n"
            f"*Current state:* `{data['state']}`")

        return discord.Embed(description=msg)

    async def on_message(self, message) -> None:
        # don't let the bot reply to itself
        if message.author == self.user:
            return

        cmd_string = message.content.split(" ")
        command = cmd_string[0]
        cmd = command.replace(CMD_PREFIX_CHAR,"")

        if cmd.startswith('servers'):
            resp = []
            headers = ["NAME","IP","PORT"]
            resp.append(headers)

            for k,v in self.servers.items():
                resp.append([k,v['ip'],v['port']])
            table = tabulate(resp,headers='firstrow',tablefmt='grid')
            await message.channel.send(f"```{table}```")
        elif cmd.startswith('help'):
            msg = f"**Available commands:**\n"
            for k,v in self.available_calls.items():
                msg += f"{v.__doc__}"
            await message.channel.send(embed=discord.Embed(description=msg))
        else:
            cmd_args = []
            params = {}
            try:
                if len(self.servers) == 1:
                    server = list(self.servers.keys())[0]
                    if len(cmd_string) > 1:
                        cmd_args = cmd_string[1:]
                else:
                    if len(cmd_string) > 1:
                        server = cmd_string[1]
                        if server not in self.servers:
                            await message.channel.send((
                                f"More than one server available, but no server specified. Use:\n"
                                f"{self.available_calls[cmd].__doc__}"
                            ))
                            return None
                    else:
                        await message.channel.send((
                            f"More than one server available, but no server specified. Use:\n"
                            f"{self.available_calls[cmd].__doc__}"
                        ))
                        return None

                    if len(cmd_string) > 2:
                        cmd_args = cmd_string[2:]
                        params = self.parse_command_args(cmd, cmd_args)

                js = (await self.process_command(server, cmd, params))
                func = self.available_calls[cmd]
                embed = func(server, js, *cmd_args)
                if embed is not None:
                    if isinstance(embed, Embed):
                        await message.channel.send(embed=embed)
                    elif isinstance(embed, List):
                        for m in embed:
                            await message.channel.send(embed=m)
                    else:
                        await message.channel.send(embed)
            except Exception as e:
                await message.channel.send(f"There was an error. Please check the ft_bot logs.")
                traceback.print_exc()
                logger.error("You got frogged: ", e)

    def parse_command_args(self, cmd, *command_args):
        params = {}

        if len(command_args) > 0:
            if cmd in ['daily','weekly','monthly']:
                params['timescale'] = command_args[0]
            elif cmd in ['trades']:
                params['limit'] = command_args[0]
            elif cmd in ['status']:
                params['trade_ids'] = command_args

        return params

class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

def decimals_per_coin(coin: str):
    """
    Helper method getting decimal amount for this coin
    example usage: f".{decimals_per_coin('USD')}f"
    :param coin: Which coin are we printing the price / value for
    """

    DECIMAL_PER_COIN_FALLBACK = 3  # Should be low to avoid listing all possible FIAT's
    DECIMALS_PER_COIN = {
        'BTC': 8,
        'ETH': 5,
    }

    return DECIMALS_PER_COIN.get(coin, DECIMAL_PER_COIN_FALLBACK)

def round_coin_value(
        value: float, coin: str, show_coin_name=True, keep_trailing_zeros=False) -> str:
    """
    Get price value for this coin
    :param value: Value to be printed
    :param coin: Which coin are we printing the price / value for
    :param show_coin_name: Return string in format: "222.22 USDT" or "222.22"
    :param keep_trailing_zeros: Keep trailing zeros "222.200" vs. "222.2"
    :return: Formatted / rounded value (with or without coin name)
    """
    val = f"{value:.{decimals_per_coin(coin)}f}"
    if not keep_trailing_zeros:
        val = val.rstrip('0').rstrip('.')
    if show_coin_name:
        val = f"{val} {coin}"

    return val

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

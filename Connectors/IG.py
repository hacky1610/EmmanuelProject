import json
import os.path
import time
import traceback
from typing import Dict, List, Optional
from trading_ig import IGService
from trading_ig.rest import IGException, ApiExceededException
from BL import DataProcessor, BaseReader
from BL.analytics import Analytics
from BL.datatypes import TradeAction
from BL.indicators import Indicators
from Connectors.deal_store import DealStore, Deal
from Connectors.market_store import MarketStore
from Connectors.predictore_store import PredictorStore
from Predictors.deep_predictor import DeepPredictor
from Predictors.generic_predictor import GenericPredictor
from Predictors.utils import TimeUtils
from Tracing.ConsoleTracer import ConsoleTracer
from Tracing.Tracer import Tracer
import plotly.graph_objects as go
import pandas as pd
from pandas import DataFrame, Series
import re
import tempfile
from datetime import datetime, timedelta
from Connectors.tiingo import TradeType
from UI.base_viewer import BaseViewer


class IG:
    BUY_DIRECTION = "BUY"
    SELL_DIRECTION = "SELL"

    def __init__(self,
                 conf_reader: BaseReader,
                 tracer: Tracer = ConsoleTracer(),
                 live: bool = False,
                 connect:bool = True):
        self.ig_service = None
        self.user = conf_reader.get("ig_demo_user")
        self.password = conf_reader.get("ig_demo_pass")
        self.key = conf_reader.get("ig_demo_key")
        self.accNr = conf_reader.get("ig_demo_acc_nr")
        if live:
            self.type = "LIVE"
            self._fx_id = 342535
            self._crypto_id = None
            self._gold_id = None
            self._silver_id = None
        else:
            self.type = "DEMO"
            self._fx_id = 264139
            self._crypto_id = 1002200
            self._gold_id = 104139
            self._silver_id = 264211
        self._tracer: Tracer = tracer
        if connect:
            self.connect()
        self._excludedMarkets = ["CHFHUF", "EMFX USDTWD ($1 Contract)", "EMFX USDPHP ($1 Contract)",
                                 "EMFX USDKRW ($1 Contract)",
                                 "EMFX USDINR ($1 Contract)", "EMFX USDIDR ($1 Contract)", "EMFX INRJPY",
                                 "EMFX GBPINR (1 Contract)", "NZDGBP",
                                 "NZDEUR", "NZDAUD", "AUDGBP", "AUDEUR", "GBPEUR"]

        self._symbol_reference = {
            "CS.D.BCHUSD.CFD.IP":
                {
                    "symbol": "BCHUSD",
                    "size": 1,
                    "currency": "USD"
                },
            "CS.D.BCHUSD.CFE.IP":
                {
                    "symbol": "BCHEUR",
                    "size": 1,
                    "currency": "EUR"
                },
            # Gold
            "CS.D.CFDGOLD.CFDGC.IP":
                {
                    "symbol": "XAUUSD",
                    "size": 1,
                    "currency": "USD"
                },
            # Silber
            "CS.D.CFDSILVER.CFM.IP":
                {
                    "symbol": "XAGUSD",
                    "size": 0.5,
                    "currency": "USD"
                }
        }

    def _get_markets_by_id(self, id):

        counter = 0
        res = None
        while counter < 4:
            try:
                res = self.ig_service.fetch_sub_nodes_by_node(id)
                break
            except ApiExceededException:
                self._tracer.debug("ApiExceededException")
                time.sleep(60)
                counter += 1
            except Exception as e:
                traceback_str = traceback.format_exc()  # Das gibt die Traceback-Information als String zurück
                self._tracer.debug(f"MainException: {e} File:{traceback_str}")
                time.sleep(60)
                return DataFrame()

        if res is None:
            traceback_str = traceback.format_exc()  # Das gibt die Traceback-Information als String zurück
            print(f"MainException:  File:{traceback_str}")
            return DataFrame()

        if len(res["nodes"]) > 0:
            markets = DataFrame()
            for i in res["nodes"].id:
                markets = markets.append(self._get_markets_by_id(i))
            return markets
        else:
            return res["markets"]

    def _set_symbol(self, markets):
        for m in markets:
            epic = m["epic"]
            if epic in self._symbol_reference:
                m["symbol"] = self._symbol_reference[epic]["symbol"]
                m["size"] = self._symbol_reference[epic]["size"]
                m["currency"] = self._symbol_reference[epic]["currency"]

        return markets

    def get_markets(self, trade_type: TradeType, tradeable: bool = True) -> DataFrame:
        if trade_type == TradeType.FX:
            return self._get_markets(self._fx_id, tradeable)
        elif trade_type == TradeType.CRYPTO:
            markets = self._get_markets(self._crypto_id, tradeable)  # 668997 is only Bitcoin Cash
            return self._set_symbol(markets)
        elif trade_type == TradeType.METAL:
            gold = self._get_markets(self._gold_id, tradeable)  # Gold
            silver = self._get_markets(self._silver_id, tradeable)
            return self._set_symbol(gold + silver)

        return DataFrame()

    def get_market_details(self, epic: str):
        return self.ig_service.fetch_market_by_epic(epic)

    @staticmethod
    def _get_spread(market_object):
        offer = market_object.offer
        bid = market_object.bid
        scaling = market_object.scalingFactor

        if offer is not None and bid is not None:
            return (offer - bid) * scaling

        return 0

    def _get_markets(self, id: int, tradebale: bool = True):
        market_df = self._get_markets_by_id(id)
        if len(market_df) == 0:
            return DataFrame()

        markets = []
        if tradebale:
            market_df = market_df[market_df.marketStatus == "TRADEABLE"]
        for market in market_df.iterrows():
            symbol = (market[1].instrumentName.replace("/", "").replace(" Mini", "")).strip()
            if symbol not in self._excludedMarkets:
                markets.append({
                    "symbol": symbol,
                    "epic": market[1].epic,
                    "spread": self._get_spread(market[1]),
                    "scaling": market[1].scalingFactor,
                    "size": 1.0,
                    "currency": self.get_currency(market[1].epic)
                })

        return markets

    def get_deal_by_reference(self, reference):
        return self.ig_service.fetch_deal_by_deal_reference(reference)

    def connect(self):
        # no cache
        self._tracer.debug(f"Connect {self.type} {self.user} {self.accNr}")
        self.ig_service = IGService(
            self.user, self.password, self.key, self.type, acc_number=self.accNr
        )
        try:
            self.ig_service.create_session()
        except Exception as ex:
            self._tracer.error(f"Error during open a IG Connection {ex}")

    @staticmethod
    def get_currency(epic: str):
        m = re.match("[\w]+\.[\w]+\.[\w]{3}([\w]{3})\.", epic)
        if m != None and len(m.groups()) == 1:
            currency = m.groups()[0]
            if currency == "TRY":
                return "TRL"
            return currency
        return "USD"

    def buy(self,
            epic: str,
            stop: int,
            limit: int,
            size: float = 1.0,
            currency: str = "USD") -> (bool, str):
        return self.open(epic, IG.BUY_DIRECTION, stop, limit, size, currency)

    def sell(self,
             epic: str,
             stop: int,
             limit: int,
             size: float = 1.0,
             currency: str = "USD") -> (bool, str):
        return self.open(epic, IG.SELL_DIRECTION, stop, limit, size, currency)

    def open(self,
             epic: str,
             direction: str,
             stop: int = 25,
             limit: int = 25,
             size: float = 1.0,
             currency: str = "USD") -> (bool, dict):

        deal_response: dict = {}
        result = False
        try:
            self._tracer.debug(
                f"Open trade for {epic} with {direction} {currency} Size {size} Stop {stop} Limit {limit} ")
            response = self.ig_service.create_open_position(
                currency_code=currency,
                direction=direction,
                epic=epic,
                expiry="-",
                force_open=True,
                guaranteed_stop=False,
                order_type="MARKET",
                size=size,
                level=None,
                limit_distance=limit,
                limit_level=None,
                quote_id=None,
                stop_distance=stop,
                stop_level=None,
                trailing_stop=False,
                trailing_stop_increment=None
            )
            if response["dealStatus"] != "ACCEPTED":
                if response['reason'] == "MARKET_OFFLINE":
                    self._tracer.warning(f"{response['reason']} for {epic}. Details {response}")
                    result = True
                else:
                    self._tracer.error(f"could not open trade: {response['reason']} for {epic}. Details {response}")
            else:
                self._tracer.write(f"Opened successfull {epic}. Deal details {response}")
                result = True
            deal_response = response
        except IGException as ex:
            self._tracer.error(f"Error during open a position. {ex} for {epic}")

        return result, deal_response

    def has_opened_positions(self):
        positions = self.ig_service.fetch_open_positions()
        return len(positions) > 0

    def get_opened_position_ids_by_direction(self, direction: str):
        positions = self.ig_service.fetch_open_positions()
        return positions.loc[positions["direction"] == direction]

    def get_opened_positions(self) -> DataFrame:
        return self.ig_service.fetch_open_positions()

    def get_min_stop_distance(self, epic: str) -> float:
        market = IG.get_market_by_epic(epic)
        return market["min_stop_disance"]

    def get_min_stop_distance_online(self, epic: str) -> float:
        try:
            ms = self.get_market_details(epic)
            return ms["dealingRules"]["minNormalStopOrLimitDistance"]["value"]
        except Exception as e:
            self._tracer.error(f"Error while get limit {e}")
            return -1

    def get_stop_distance(self, market, epic: str, scaling_factor: int,
                          intelligent_stop_distance: float = 6.0,
                          check_min=True) -> (float, bool):
        stop_distance = market.get_pip_value(euro=intelligent_stop_distance,
                                             scaling_factor=scaling_factor)

        if check_min:
            min_stop_distance = self.get_min_stop_distance(epic) / scaling_factor * 1.05
        else:
            min_stop_distance = 0

        if stop_distance <= min_stop_distance:
            self._tracer.debug(
                f"The calculated stop distance {stop_distance} is smaller than the min {min_stop_distance}")
            return min_stop_distance, True

        self._tracer.debug(f"Calculated stop distance is {stop_distance}")

        return stop_distance, False

    def is_ready_to_set_intelligent_stop(self, diff, limit: float) -> bool:

        ready = diff > limit
        if ready:
            self._tracer.debug(f"Current profit {diff} is greate than limit {limit}")
        return ready

    def _get_atr(self, tiingo, symbol:str):
        df = tiingo.load_trade_data(symbol=symbol, dp=DataProcessor(), trade_type=TradeType.FX)
        return df.iloc[-1].ATR

    def set_intelligent_stop_level(self, position, deal, deal_store, scaling, tiingo):
        """Hauptmethode zur intelligenten Anpassung des Stop-Levels."""
        open_price = position.level
        bid_price = position.bid
        stop_level = position.stopLevel
        limit_level = position.limitLevel
        direction = position.direction
        deal_id = position.dealId
        ticker = position.instrumentName.replace("/", "").replace(" Mini", "")
        atr = self._get_atr(tiingo, ticker)
        min_stop_distance = max(self.get_min_stop_distance(deal.epic) / scaling, 0.5 * atr)
        self._tracer.info(f" Dynamische Mindest-Stop-Distanz: {min_stop_distance}")

        self._tracer.info(f"{ticker} {direction} Trade {deal_id}")
        self._tracer.info(f" Open: {open_price}, Bid: {bid_price}, Stop: {stop_level}, Limit: {limit_level}, ATR: {atr}")

        profit_percent, _ = self._calculate_profit_percentage(direction, open_price, limit_level, bid_price)
        self._tracer.info(f" Trade {deal_id} - Gewinn: {profit_percent:.2f}%")

        # 1️⃣ Prüfen, ob der manuelle Stop erreicht wurde
        if deal.is_manual_stop and bid_price <= deal.manual_stop_level:
            self._tracer.warning(f" #######Trade {deal_id} erreicht manuellen Stop bei {deal.manual_stop_level} -> Schließe Trade!")
            self._close_trade(deal_id, deal.size, direction)
            return {"status": "closed", "message": f"Trade geschlossen bei {deal.manual_stop_level}"}

        # 2️⃣ Berechnung des neuen Stop-Levels
        new_stop_level = self._calculate_new_stop(stop_level, bid_price, atr, profit_percent)
        self._tracer.info(f" Neuer berechneter Stop: {new_stop_level}")

        new_stop_level = self._apply_break_even_stop(new_stop_level, open_price, stop_level, 0, profit_percent)
        self._tracer.info(f" Break-Even angepasst: {new_stop_level}")

        limit_level = self._adjust_limit_level(limit_level, atr, profit_percent)

        # 3️⃣ Stop-Level validieren
        if abs(new_stop_level - bid_price) < min_stop_distance:
            self._tracer.warning(f"Neuer Stop {new_stop_level} ist zu nah am Preis {bid_price}. Verwende manuellen Stop.")

            if not deal.is_manual_stop or new_stop_level > deal.manual_stop_level:
                deal.manual_stop_level = new_stop_level
                deal.is_manual_stop = True
                self._tracer.info(f"######Manuellen Stop auf {new_stop_level} gesetzt#########")

            provider_stop_level = bid_price - min_stop_distance
            self._tracer.info(f" Trading-Provider bekommt stattdessen Stop-Level: {provider_stop_level}")
        else:
            provider_stop_level = new_stop_level
            deal.is_manual_stop = False
            self._tracer.info(f" Stop-Level {provider_stop_level} ist gültig. Kein manueller Stop nötig.")

        deal_store.save(deal)

        # ATR-Faktoren berechnen
        limit_atr_factor = (limit_level - bid_price) / atr if limit_level else None
        manual_stop_atr_factor = (deal.manual_stop_level - bid_price) / atr if deal.is_manual_stop else None
        provider_stop_atr_factor = (provider_stop_level - bid_price) / atr

        # Log der ATR-Faktoren
        self._tracer.info(
            f"++++ATR-Faktoren für Trade {deal_id}: "
            f"Limit: {limit_atr_factor:.2f} ATR, "
            f"Manueller Stop: {manual_stop_atr_factor:.2f} ATR, "
            f"Provider Stop: {provider_stop_atr_factor:.2f} ATR"
        )

        if abs(provider_stop_level - stop_level) < 0.1 * atr:
            self._tracer.info(" Stop-Level hat sich nur minimal verändert. Kein API-Update nötig.")
            return {"status": "unchanged", "message": "Keine Anpassung erforderlich"}

        self._tracer.info(f"#######Provider Stop auf {provider_stop_level} gesetzt.#######")
        self._adjust_stop_level(deal_id, limit_level, provider_stop_level, deal_store)
        return {"status": "success", "message": "Stop-Level aktualisiert"}

    def _adjust_limit_level(self, limit_level, atr, profit_percent):
        """Erhöht das Limit-Level um 0.5 ATR, wenn der Preis > 80% des Limits ist."""
        if profit_percent > 80 and limit_level:
            self._tracer.debug("new limit")
            return limit_level + 0.5 * atr
        return limit_level

    def _calculate_new_stop(self, stop_level, bid_price, atr, profit_percent):
        """Berechnet das neue Stop-Level mit dynamischen ATR-Multiplikatoren."""
        atr_multiplier = max(1.0, 2.0 - (profit_percent / 100))  # Dynamischer Faktor

        new_stop = max(stop_level, bid_price - (atr_multiplier * atr))
        self._tracer.info(f" ATR Multiplikator: {atr_multiplier}, Neuer Stop: {new_stop}")
        return new_stop

    def _apply_break_even_stop(self, new_stop_level, open_price, stop_level, spread, profit_percent):
        """Setzt den Stop auf Break-Even, wenn >50% Gewinn erreicht sind."""
        if profit_percent > 50 and stop_level < open_price:
            return max(new_stop_level, open_price + spread)
        return new_stop_level

    def _close_trade(self, deal_id, size, direction):
        """Schließt den Trade basierend auf der Richtung."""
        close_direction = IG.SELL_DIRECTION if direction == IG.BUY_DIRECTION else IG.BUY_DIRECTION
        self.close(close_direction, deal_id, size)

    def _calculate_profit_percentage(self, direction, open_price, limit_level, bid_price):
        """Berechnet die aktuelle Profit-Rate."""
        current_diff = (bid_price - open_price) if direction == IG.BUY_DIRECTION else (open_price - bid_price)
        max_possible_profit = (limit_level - open_price) if direction == IG.BUY_DIRECTION else (
                    open_price - limit_level)
        max_possible_profit = max_possible_profit if max_possible_profit != 0 else current_diff
        profit_percent = (current_diff / max_possible_profit) * 100 if max_possible_profit != 0 else 0
        return profit_percent, max_possible_profit


    def manual_close(self, position: Series, deal_store: DealStore):
        bid_price = position.bid
        offer_price = position.offer
        direction = position.direction
        deal_id = position.dealId
        deal = deal_store.get_deal_by_deal_id(deal_id)

        if deal.is_manual_stop:
            self._tracer.debug("Manual Stop")

            if direction == TradeAction.BUY:
                self._tracer.debug(f"Bid {bid_price} Stop {deal.manual_stop_level}")
                if bid_price < deal.manual_stop_level:
                    self._tracer.debug(f"Stop reached {deal}")
                    self.close(IG.SELL_DIRECTION, deal_id, deal.size)
            if direction == TradeAction.SELL:
                self._tracer.debug(f"Offer {offer_price} Stop {deal.manual_stop_level}")
                if offer_price > deal.manual_stop_level:
                    self._tracer.debug(f"Stop reached {deal}")
                    self.close(IG.BUY_DIRECTION, deal_id, deal.size)

    def manual_close_after_time(self, position: Series, deal_store: DealStore, predictor_store: PredictorStore,
                                time_threshold_minutes=10):
        """
          Schließt Trades manuell, wenn die Zeit die Handelszeit (plus Threshold) überschreitet.

          Args:
              position (Series): Die aktuelle Position mit Details wie bid, offer, direction, und dealId.
              deal_store (DealStore): Speicher für die Handelsdetails.
              predictor_store (PredictorStore): Speicher für die Vorhersageparameter.
              time_threshold_minutes (int): Zeit-Threshold in Minuten, standardmäßig 10 Minuten.
          """
        # Extrahiere Position-Details
        direction = position.direction
        deal_id = position.dealId

        # Lade das zugehörige Deal-Objekt
        deal = deal_store.get_deal_by_deal_id(deal_id)
        open_time = deal.get_open_time()  # Öffnungszeit des Trades
        p_id = deal.get_predictor_scan_id()

        # Setup des Predictors
        predictor = DeepPredictor(cache=None, config=None, indicators=Indicators(), symbol="")
        predictor_config = predictor_store.load_by_id(p_id)
        if not predictor_config:
            self._tracer.warning("No predictor config")
            return
        predictor.setup(predictor_config)

        # Handelsrichtung überprüfen
        if direction == IG.BUY_DIRECTION:
            # Erlaubte Handelszeit und Threshold berechnen
            trading_hours = predictor.get_trading_hours()
            close_time = open_time + timedelta(hours=trading_hours)
            close_time_with_threshold = close_time - timedelta(minutes=time_threshold_minutes)

            # Überprüfen, ob die Zeit überschritten wurde
            if datetime.utcnow() > close_time_with_threshold:
                self._tracer.info(
                    f"Schließe Kauf-Trade {deal_id}, da die Zeit überschritten ist {trading_hours} {open_time} {close_time} {close_time_with_threshold}")
                self.close(IG.SELL_DIRECTION, deal_id, deal.size)
            else:
                self._tracer.debug(
                    f"Trade{deal_id} ist noch im Zeitrahmen wird geschlossen {close_time_with_threshold}")

        elif direction == IG.SELL_DIRECTION:
            # Erlaubte Handelszeit und Threshold berechnen
            trading_hours = predictor.get_trading_hours()
            close_time = open_time + timedelta(hours=trading_hours)
            close_time_with_threshold = close_time - timedelta(minutes=time_threshold_minutes)

            # Überprüfen, ob die Zeit überschritten wurde
            if datetime.utcnow() > close_time_with_threshold:
                self._tracer.info(
                    f"Schließe Verkauf-Trade {deal_id}, da die Zeit überschritten ist {trading_hours} {open_time} {close_time} {close_time_with_threshold}")
                self.close(IG.BUY_DIRECTION, deal_id, deal.size)
            else:
                self._tracer.debug(
                    f"Trade{deal_id} ist noch im Zeitrahmen wird geschlossen {close_time_with_threshold}")

    def _adjust_stop_level(self, deal_id: str, limit_level: float, new_stop_level: float, deal_store: DealStore):
        self._tracer.debug(f"Change Stop level to {new_stop_level}")
        res = self.adapt_stop_level(deal_id=deal_id, limit_level=limit_level, stop_level=new_stop_level)
        self._tracer.debug(res)
        if res["dealStatus"] != "ACCEPTED":
            self._tracer.error("Stop level cant be adapted")
        else:
            deal = deal_store.get_deal_by_deal_id(deal_id)
            if deal is not None:
                deal.set_intelligent_stop_level(new_stop_level)
                deal_store.save(deal)
            else:
                self._tracer.debug(f"deal {deal_id} is not in our db")

    def adapt_stop_level(self, deal_id: str, limit_level: float, stop_level: float):

        return self.ig_service.update_open_position(deal_id=deal_id, limit_level=limit_level,
                                                    stop_level=stop_level)

    def get_opened_positions_by_epic(self, epic: str) -> DataFrame:
        positions = self.get_opened_positions()
        return positions[positions.epic == epic]

    def get_transaction_history(self, days: int) -> DataFrame:
        df_list = []
        for i in range(days):
            transactions = self.ig_service.fetch_transaction_history(
                trans_type="ALL_DEAL",
                page_size=50,
                max_span_seconds=60 * 60 * 24 * days,
                page_number=i
            )
            df_list.append(transactions)

        return pd.concat(df_list, ignore_index=True)

    def get_current_balance(self):
        balance = self.ig_service.fetch_accounts().loc[0].balance
        if balance is None:
            return 0
        return balance

    def close(self,
              direction: str,
              deal_id: str,
              size: float = 1.0, ) -> (bool, dict):

        deal_response: dict = {}
        result = False
        try:
            response = self.ig_service.close_open_position(
                direction=direction,
                epic=None,
                expiry="-",
                order_type="MARKET",
                size=size,
                level=None,
                quote_id=None,
                deal_id=deal_id
            )
            if response["dealStatus"] != "ACCEPTED":
                self._tracer.error(f"could not close trade: {response['reason']}")
            else:
                self._tracer.write(f"Close successfull {deal_id}. Deal details {response}")
                result = True
            deal_response = response
        except IGException as ex:
            self._tracer.error(f"Error during close a position. {ex} for {deal_id}")

        return result, deal_response

    @staticmethod
    def _get_hours(start_date):
        start_time = pd.to_datetime(start_date.openDateUtc.values[0])
        first_hours = datetime(start_time.year, start_time.month, start_time.day, start_time.hour)
        hours = [first_hours]
        for i in range(23):
            hours.append(hours[i] + timedelta(hours=1))

        return hours

    @staticmethod
    def fix_hist(hist):
        new_column = []
        for values in hist.instrumentName:
            res = re.search(r'\w{3}\/\w{3}', values)
            if res is not None:
                new_column.append(re.search(r'\w{3}\/\w{3}', values).group().replace("/", ""))
            else:
                new_column.append("Unknown")
        hist['name'] = new_column

        hist['profitAndLoss'] = hist.profitAndLoss.str.replace("E", "").astype(float)

        return hist

    @staticmethod
    def _print_open(fig, df, symbol):
        fig.add_scatter(x=df["openDateUtc"],
                        y=df["openLevel"],
                        marker=dict(
                            color='Blue',
                            size=10,
                            symbol=symbol
                        ),
                        )

    @staticmethod
    def _print_result(fig, df, color):
        fig.add_scatter(x=df["dateUtc"],
                        y=df["closeLevel"],
                        marker=dict(
                            color=color,
                            size=10
                        ),
                        )

    @staticmethod
    def _print_win(fig, df):
        IG._print_result(fig, df, "Green")

    @staticmethod
    def _print_loose(fig, df):
        IG._print_result(fig, df, "Red")

    @staticmethod
    def _print_long_open(fig, df):
        IG._print_open(fig, df, "triangle-up")

    @staticmethod
    def _print_short_open(fig, df):
        IG._print_open(fig, df, "triangle-down")

    @staticmethod
    def _print_stop_limit():
        pass
        # stopLine, = plt.plot([row.openDateUtc, row.dateUtc], [row.openLevel + pl, row.openLevel + pl],
        #                     color="#ff0000")
        # limitLine, = plt.plot([row.openDateUtc, row.dateUtc], [row.openLevel - pl, row.openLevel - pl],
        #                      color="#00ff00", label="Limit")

    @staticmethod
    def report_symbol(ti, ticker, start_time_hours, start_time_str, hist, cache, dp, analytics: Analytics,
                      viewer: BaseViewer, predictor_settings: Dict):
        df_results = DataFrame()
        df_history = ti.load_data_by_date(ticker,
                                          TimeUtils.get_date_string(start_time_hours),
                                          None,
                                          DataProcessor(),
                                          validate=False)

        df_hour = df_history[df_history["date"] > start_time_str]

        temp_hist = hist[hist['name'] == ticker]

        add_text = ""
        for r in temp_hist.iterrows():
            row = r[1]
            t = (str(row.openDateUtc)).replace(" ", "T")
            n = row["name"]
            name = f"{t}_{n}"
            deal_info = cache.load_deal_info(name)
            if deal_info != None:
                win_lost = deal_info["_wins"] / deal_info["_trades"]
                add_text += f"{deal_info['Type']}: WL: {win_lost} - Trades: {deal_info['_trades']}"
                predictor = GenericPredictor(indicators=Indicators(), symbol="")
                predictor.setup(deal_info)
                predictor.setup(predictor_settings)
                df, df_eval = ti.load_train_data(n, dp, TradeType.FX)
                dt = datetime.fromisoformat(str(row.openDateUtc))
                filter = datetime(dt.year, dt.month, dt.day, dt.hour) - timedelta(hours=1)
                open_data = (df[df.date == TimeUtils.get_time_string(filter)]).iloc[0]
                open_data["predictor"] = deal_info['Type']
                open_data["ticker"] = ticker
                if row.profitAndLoss > 0:
                    open_data["wl"] = "won"
                else:
                    open_data["wl"] = "lost"
                open_data["action"] = deal_info["direction"].lower()
                open_data["eval_result"] = "none"
                open_data["eval_action"] = "none"
                open_data["trades"] = deal_info["_trades"]
                open_data["wl_ration"] = win_lost

                df_results = df_results.append(open_data)
                res = analytics.evaluate(predictor, df, df_eval, name,
                                         time_filter=datetime(dt.year, dt.month, dt.day, dt.hour))
                for trade in res.get_trade_results():
                    if TimeUtils.get_time_string(datetime(dt.year, dt.month, dt.day, dt.hour)) == trade.open_time:
                        df_results.loc[
                            df_results.date == TimeUtils.get_time_string(filter), "eval_result"] = trade.result
                        df_results.loc[
                            df_results.date == TimeUtils.get_time_string(filter), "eval_action"] = trade.action
            else:
                raise Exception()

        winner = temp_hist[temp_hist["profitAndLoss"] >= 0]
        looser = temp_hist[temp_hist["profitAndLoss"] < 0]

        long_winner = winner[winner["closeLevel"] >= winner["openLevel"]]
        short_winner = winner[winner["closeLevel"] <= winner["openLevel"]]

        long_looser = looser[looser["closeLevel"] < looser["openLevel"]]
        short_looser = looser[looser["closeLevel"] > looser["openLevel"]]

        shorts = short_winner.append(short_looser)
        longs = long_winner.append(long_looser)

        fig = go.Figure(data=[
            go.Candlestick(x=df_hour['date'],
                           open=df_hour['open'],
                           high=df_hour['high'],
                           low=df_hour['low'],
                           close=df_hour['close']),
        ])

        # Open
        IG._print_long_open(fig, longs)
        IG._print_short_open(fig, shorts)

        # result
        IG._print_win(fig, winner)
        IG._print_loose(fig, looser)

        fig.update_layout(
            title=f"Live trade of  <a href='https://de.tradingview.com/chart/?symbol={ticker}'>{ticker}</a> {add_text}",
            legend_title="Legend Title",
        )
        fig.show()

        # if len(df_results[df_results.action != df_results.eval_action]) > 0:
        #     print(f"{ticker} ERROR- action mismatch")
        #
        # if len(df_results[df_results.wl != df_results.eval_result]) > 0:
        #     print(f"{ticker} ERROR - evaluation mismatch")
        return df_results

    @staticmethod
    def get_markets_offline() -> List[Dict]:
        _currency_markets = []
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "Data", "markets.json"),
                  'r') as json_file:
            _currency_markets = json.load(json_file)

        return _currency_markets

    @staticmethod
    def get_market_by_epic(market_epic: str) -> Optional[Dict]:
        _currency_markets = IG.get_markets_offline()
        for market in _currency_markets:
            if market.get('epic') == market_epic:
                return market
        return None

    @staticmethod
    def set_markets_offline(currency_markets: List[Dict]):
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "Data", "markets.json"),
                  'w') as json_file:
            json.dump(currency_markets, json_file, indent=4)

    def report_last_day(self, ti, cache, dp, analytics, viewer: BaseViewer, days: int = 7):
        start_time = (datetime.now() - timedelta(hours=days * 24))
        start_time_hours = (datetime.now() - timedelta(days=days * 2))
        start_time_str = start_time.strftime("%Y-%m-%dT%H:%M:%S")

        hist = self.get_transaction_history(start_time)
        if len(hist) == 0:
            return

        hist = hist.set_index("openDateUtc")
        hist.sort_index(inplace=True)
        hist.reset_index(inplace=True)

        hist["openDateUtc"] = pd.to_datetime(hist["openDateUtc"])
        hist["dateUtc"] = pd.to_datetime(hist["dateUtc"])
        hist["openLevel"] = hist["openLevel"].astype("float")
        hist["closeLevel"] = hist["closeLevel"].astype("float")

        hist = self.fix_hist(hist)

        for i in [""] + Indicators().get_all_indicator_names():
            print(f"Indicator {i}")
            df_results = DataFrame()
            for ticker in hist['name'].unique():
                df_res = self.report_symbol(ti=ti,
                                            ticker=ticker,
                                            start_time_hours=start_time_hours,
                                            start_time_str=start_time_str,
                                            hist=hist,
                                            cache=cache,
                                            dp=dp,
                                            analytics=analytics,
                                            viewer=viewer,
                                            predictor_settings={"_additional_indicators": [i]})
                df_results = df_results.append(df_res)
            print(df_results)

            # print(df_results.filter(["date","ticker", "wl", "eval_result"]))
            try:
                wl_eval = len(df_results[df_results.eval_result == 'won']) / (
                        len(df_results[df_results.eval_result == 'won']) + len(
                    df_results[df_results.eval_result == 'lost']))
                wl_original = len(df_results[df_results.wl == 'won']) / (
                        len(df_results[df_results.wl == 'won']) + len(df_results[df_results.wl == 'lost']))
                print(f"WL   Original: {wl_original} Eval: {wl_eval}")
                print(
                    f"Lost Original: {len(df_results[df_results.wl == 'lost'])} Eval: {len(df_results[df_results.eval_result == 'lost'])}")
            except:
                print("Division by Zero")

    def report_summary(self,
                       ti,
                       dp_service,
                       delta: timedelta = timedelta(hours=24),
                       name: str = "lastday"):
        start_time = (datetime.now() - delta)

        hist = self.get_transaction_history(start_time)
        if len(hist) == 0:
            return

        hist = self.fix_hist(hist)

        summary_text = f"Summary {name}"

        all_profit = hist.profitAndLoss.sum()
        balance = self.get_current_balance()

        profit_percentige = (balance * 100 / (balance - all_profit)) - 100

        summary_text += f"\n\rProfit: {all_profit}€"
        summary_text += f"\n\rPerformance: {profit_percentige}%"
        summary_text += f"\n\rWin_Loss: {len(hist[hist.profitAndLoss > 0]) / len(hist)}"
        summary_text += f"\n\r|Ticker| Profit| Mean |"
        summary_text += f"\n\r|------| ------| ---- |"
        for ticker in hist['name'].unique():
            temp_hist = hist[hist['name'] == ticker]
            profit = temp_hist.profitAndLoss.sum()
            mean = temp_hist.profitAndLoss.mean()
            summary_text += f"\n|{ticker}| {profit} | {mean}"

        temp_file = os.path.join(tempfile.gettempdir(), f"summary_{name}.md")

        with open(temp_file, "w") as f:
            f.write(summary_text)

        dp_service.upload_file(temp_file, f"{datetime.now().strftime('%Y_%m_%d')}/summary_{name}.md")

        return

    def create_report(self, ti, dp_service, predictor, cache, dp, analytics, viewer: BaseViewer):
        # self.report_summary(ti, dp_service, timedelta(hours=24), "lastday")
        # self.report_summary(ti=ti,
        #                     dp_service=dp_service,
        #                     delta=timedelta(days=7),
        #                     name="lastweek")
        self.report_last_day(ti=ti, cache=cache, dp=dp, analytics=analytics, viewer=viewer, days=8)

import json
import logging
from d3a.models.strategy.external_strategies import IncomingRequest
from d3a.models.strategy.storage import StorageStrategy
from d3a.models.strategy.external_strategies import ExternalMixin, check_for_connected_and_reply


class StorageExternalMixin(ExternalMixin):
    """
    Mixin for enabling an external api for the storage strategies.
    Should always be inherited together with a superclass of StorageStrategy.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pending_requests = []

    def event_activate(self):
        super().event_activate()
        self.redis.sub_to_multiple_channels({
            f'{self.channel_prefix}/register_participant': self._register,
            f'{self.channel_prefix}/unregister_participant': self._unregister,
            f'{self.channel_prefix}/offer': self._offer,
            f'{self.channel_prefix}/delete_offer': self._delete_offer,
            f'{self.channel_prefix}/offers': self._list_offers,
            f'{self.channel_prefix}/bid': self._bid,
            f'{self.channel_prefix}/delete_bid': self._delete_bid,
            f'{self.channel_prefix}/bids': self._list_bids,
            f'{self.channel_prefix}/stats': self._area_stats
        })

    def _list_offers(self, payload):
        list_offers_response_channel = f'{self.channel_prefix}/response/offers/response'
        if not check_for_connected_and_reply(self.redis, list_offers_response_channel,
                                             self.connected):
            return
        try:
            filtered_offers = [{"id": v.id, "price": v.price, "energy": v.energy}
                               for _, v in self.market.get_offers().items()
                               if v.seller == self.device.name]
            self.redis.publish_json(
                list_offers_response_channel,
                {"command": "offers", "status": "ready", "offer_list": filtered_offers})
        except Exception as e:
            logging.error(f"Error when handling list offers on area {self.device.name}: "
                          f"Exception: {str(e)}")
            self.redis.publish_json(
                list_offers_response_channel,
                {"command": "offers", "status": "error",
                 "error_message": f"Error when listing offers on area {self.device.name}."})

    def _delete_offer(self, payload):
        delete_offer_response_channel = f'{self.channel_prefix}/response/delete_offer'
        if not check_for_connected_and_reply(self.redis, delete_offer_response_channel,
                                             self.connected):
            return
        try:
            arguments = json.loads(payload["data"])
            assert set(arguments.keys()) == {'offer'}
        except Exception as e:
            logging.error(f"Error when handling delete offer request. Payload {payload}. "
                          f"Exception {str(e)}.")
            self.redis.publish_json(
                delete_offer_response_channel,
                {"command": "offer_delete",
                 "error": "Incorrect delete offer request. Available parameters: (offer)."}
            )
        else:
            self.pending_requests.append(
                IncomingRequest("delete_offer", arguments, delete_offer_response_channel))

    def _delete_offer_impl(self, arguments, response_channel):
        try:
            self.market.delete_offer(arguments["offer"])
            self.offers.remove_by_id(arguments["offer"])
            self.state.offered_sell_kWh[self.market.time_slot] -= arguments["offer"]["energy"]
            self.redis.publish_json(
                response_channel,
                {"command": "offer_delete", "status": "ready",
                 "deleted_offer": arguments["offer"]})
        except Exception as e:
            logging.error(f"Error when handling offer delete on area {self.device.name}: "
                          f"Exception: {str(e)}, Offer Arguments: {arguments}")
            self.redis.publish_json(
                response_channel,
                {"command": "offer_delete", "status": "error",
                 "error_message": f"Error when handling offer delete "
                                  f"on area {self.device.name} with arguments {arguments}."})

    def _offer(self, payload):
        offer_response_channel = f'{self.channel_prefix}/response/offer'
        if not check_for_connected_and_reply(self.redis, offer_response_channel,
                                             self.connected):
            return
        try:
            arguments = json.loads(payload["data"])
            assert set(arguments.keys()) == {'price', 'energy'}
            arguments['seller'] = self.device.name
            arguments['seller_origin'] = self.device.name
            cumulative_allowed = \
                arguments['energy'] + \
                self.state.pledged_sell_kWh[self.market.time_slot] + \
                self.state.offered_sell_kWh[self.market.time_slot]
            assert cumulative_allowed <= self.state.energy_to_sell_dict[self.market.time_slot]
        except Exception as e:
            logging.error(f"Incorrect offer request. Payload {payload}. Exception {str(e)}.")
            self.redis.publish_json(
                offer_response_channel,
                {"command": "offer",
                 "error": "Incorrect offer request. Available parameters: (price, energy)."}
            )
        else:
            self.pending_requests.append(
                IncomingRequest("offer", arguments, offer_response_channel))

    def _offer_impl(self, arguments, response_channel):
        try:
            offer = self.market.offer(**arguments)
            self.offers.post(offer, self.market.id)
            self.state.offered_sell_kWh[self.market.time_slot] += offer.energy
            self.redis.publish_json(
                response_channel,
                {"command": "offer", "status": "ready", "offer": offer.to_JSON_string()})
        except Exception as e:
            logging.error(f"Error when handling offer create on area {self.device.name}: "
                          f"Exception: {str(e)}, Offer Arguments: {arguments}")
            self.redis.publish_json(
                response_channel,
                {"command": "offer", "status": "error",
                 "error_message": f"Error when handling offer create "
                                  f"on area {self.device.name} with arguments {arguments}."})

    def _list_bids(self, payload):
        list_bids_response_channel = f'{self.channel_prefix}/response/bids'
        if not check_for_connected_and_reply(self.redis, list_bids_response_channel,
                                             self.connected):
            return
        try:
            filtered_bids = [{"id": v.id, "price": v.price, "energy": v.energy}
                             for _, v in self.market.get_bids().items()
                             if v.buyer == self.device.name]
            self.redis.publish_json(
                list_bids_response_channel,
                {"command": "bids", "status": "ready", "bid_list": filtered_bids})
        except Exception as e:
            logging.error(f"Error when handling list bids on area {self.device.name}: "
                          f"Exception: {str(e)}")
            self.redis.publish_json(
                list_bids_response_channel,
                {"command": "bids", "status": "error",
                 "error_message": f"Error when listing bids on area {self.device.name}."})

    def _delete_bid(self, payload):
        delete_bid_response_channel = f'{self.channel_prefix}/response/delete_bid'
        if not check_for_connected_and_reply(self.redis,
                                             delete_bid_response_channel, self.connected):
            return
        try:
            arguments = json.loads(payload["data"])
            assert set(arguments.keys()) == {'bid'}
        except Exception:
            self.redis.publish_json(
                delete_bid_response_channel,
                {"command": "bid_delete",
                 "error": "Incorrect delete bid request. Available parameters: (bid)."}
            )
        else:
            self.pending_requests.append(
                IncomingRequest("delete_bid", arguments, delete_bid_response_channel))

    def _delete_bid_impl(self, arguments, response_channel):
        try:
            self.remove_bid_from_pending(arguments["bid"], self.market.id)
            self.state.offered_buy_kWh[self.market.time_slot] -= arguments["bid"]["energy"]
            self.redis.publish_json(
                response_channel,
                {"command": "bid_delete", "status": "ready", "bid_deleted": arguments["bid"]})
        except Exception as e:
            logging.error(f"Error when handling bid delete on area {self.device.name}: "
                          f"Exception: {str(e)}, Bid Arguments: {arguments}")
            self.redis.publish_json(
                response_channel,
                {"command": "bid_delete", "status": "error",
                 "error_message": f"Error when handling bid delete "
                                  f"on area {self.device.name} with arguments {arguments}."})

    def _bid(self, payload):
        bid_response_channel = f'{self.channel_prefix}/response/bid'
        if not check_for_connected_and_reply(self.redis, bid_response_channel, self.connected):
            return
        try:
            arguments = json.loads(payload["data"])
            assert set(arguments.keys()) == {'price', 'energy'}
            arguments['buyer_origin'] = self.device.name
            max_energy = self.state.energy_to_buy_dict[self.market.time_slot]
            cumulative_allowed = \
                arguments["energy"] + self.state.pledged_buy_kWh[self.market.time_slot] + \
                self.state.offered_buy_kWh[self.market.time_slot]
            assert cumulative_allowed <= max_energy
        except Exception:
            self.redis.publish_json(
                bid_response_channel,
                {"command": "bid",
                 "error": "Incorrect bid request. Available parameters: (price, energy)."}
            )
        else:
            self.pending_requests.append(
                IncomingRequest("bid", arguments, bid_response_channel))

    def _bid_impl(self, arguments, bid_response_channel):
        try:
            bid = self.post_bid(
                self.market,
                arguments["price"],
                arguments["energy"],
                buyer_origin=arguments["buyer_origin"]
            )
            self.state.offered_buy_kWh[self.market.time_slot] += bid.energy
            self.redis.publish_json(
                bid_response_channel,
                {"command": "bid", "status": "ready", "bid": bid.to_JSON_string()})
        except Exception as e:
            logging.error(f"Error when handling bid create on area {self.device.name}: "
                          f"Exception: {str(e)}, Bid Arguments: {arguments}")
            self.redis.publish_json(
                bid_response_channel,
                {"command": "bid", "status": "error",
                 "error_message": f"Error when handling bid create "
                                  f"on area {self.device.name} with arguments {arguments}."})

    def event_market_cycle(self):
        self.register_on_market_cycle()
        if self.connected:
            self._reset_event_tick_counter()
            self.state.market_cycle(self.market_area.current_market.time_slot,
                                    self.market.time_slot)
            self.state.clamp_energy_to_sell_kWh([self.market.time_slot])
            self.state.clamp_energy_to_buy_kWh([self.market.time_slot])
            market_event_channel = f"{self.channel_prefix}/events/market"
            current_market_info = self.market.info
            current_market_info["event"] = "market"
            current_market_info["energy_to_sell"] = \
                self.state.energy_to_sell_dict[self.market.time_slot]
            current_market_info["energy_to_buy_dict"] = \
                self.state.energy_to_buy_dict[self.market.time_slot]
            current_market_info["free_storage"] = self.state.free_storage(self.market.time_slot)
            current_market_info["used_storage"] = self.state.used_storage
            self.redis.publish_json(market_event_channel, current_market_info)
        else:
            super().event_market_cycle()

    def area_reconfigure_event(self, *args, **kwargs):
        if not self.connected:
            super().area_reconfigure_event(*args, **kwargs)

    def event_tick(self):
        if not self.connected:
            super().event_tick()
        else:
            self.state.tick(self.market_area, self.market.time_slot)

            while len(self.pending_requests) > 0:
                req = self.pending_requests.pop()
                if req.request_type == "bid":
                    self._bid_impl(req.arguments, req.response_channel)
                elif req.request_type == "delete_bid":
                    self._delete_bid_impl(req.arguments, req.response_channel)
                elif req.request_type == "offer":
                    self._offer_impl(req.arguments, req.response_channel)
                elif req.request_type == "delete_offer":
                    self._delete_offer_impl(req.arguments, req.response_channel)
                else:
                    assert False, f"Incorrect incoming request name: {req}"
            self._dispatch_event_tick_to_external_agent()


class StorageExternalStrategy(StorageExternalMixin, StorageStrategy):
    pass
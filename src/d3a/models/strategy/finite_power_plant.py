from pendulum.interval import Interval
from d3a.models.strategy import ureg
from d3a.models.strategy.commercial_producer import CommercialStrategy


class FinitePowerPlant(CommercialStrategy):
    parameters = ('energy_rate', 'max_available_power', )

    def __init__(self, energy_rate=None, max_available_power=None):
        super().__init__(energy_rate=energy_rate)
        self.max_available_power = self._sanitize_max_available_power(max_available_power)

    @staticmethod
    def _sanitize_max_available_power(max_available_power):
        if isinstance(max_available_power, int) or isinstance(max_available_power, float):
            max_available_power = {i: max_available_power for i in range(24)}
        elif isinstance(max_available_power, dict):
            latest_entry = 0
            for i in range(24):
                if i not in max_available_power:
                    max_available_power[i] = latest_entry
                else:
                    latest_entry = max_available_power[i]
        else:
            raise ValueError("Max available power should either be a numerical value, "
                             "or an hourly dict of tuples.")
        if not all(power >= 0.0 for power in max_available_power.values()):
            raise ValueError("Max available power should be positive.")
        return max_available_power

    def _markets_to_offer_on_activate(self):
        return list(self.area.markets.values())[:-1]

    def event_activate(self):
        self.energy_per_slot_wh = ureg.kWh * \
            self.max_available_power[0] / (Interval(hours=1) / self.area.config.slot_length)
        if self.energy_per_slot_wh.m <= 0.0:
            return
        super().event_activate()

    def event_trade(self, *, market, trade):
        # Disable offering more energy than the initial offer, in order to adhere to the max
        # available power.
        pass

    def event_market_cycle(self):
        target_market_time = list(self.area.markets.keys())[-1]
        self.energy_per_slot_wh = ureg.kWh * \
            self.max_available_power[target_market_time.hour] / \
            (Interval(hours=1) / self.area.config.slot_length)
        if self.energy_per_slot_wh.m <= 0.0:
            return
        super().event_market_cycle()
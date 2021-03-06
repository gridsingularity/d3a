# flake8: noqa
"""
Copyright 2018 Grid Singularity
This file is part of D3A.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
from d3a.models.area import Area
from d3a.models.strategy.storage import StorageStrategy
from d3a.models.strategy.load_hours import LoadHoursStrategy
from d3a.models.strategy.external_strategies.pv import PVExternalStrategy
from d3a.models.strategy.external_strategies.load import LoadHoursExternalStrategy
from d3a.models.strategy.external_strategies.storage import StorageExternalStrategy
from d3a_interface.constants_limits import ConstSettings

ConstSettings.IAASettings.MARKET_TYPE = 2
ConstSettings.GeneralSettings.EXPORT_OFFER_BID_TRADE_HR=False


def get_setup(config):
    area = Area(
        'Grid',
        [
            Area(
                'House 1',
                [
                    Area('H1 General Load', strategy=LoadHoursStrategy(avg_power_W=200,
                                                                       hrs_per_day=6,
                                                                       hrs_of_day=list(
                                                                           range(12, 18)),
                                                                       final_buying_rate=35)
                         ),
                    Area('H1 Storage1', strategy=StorageStrategy(initial_soc=100,
                                                                 battery_capacity_kWh=20)
                         ),
                    Area('H1 Storage2', strategy=StorageExternalStrategy(initial_soc=100,
                                                                 battery_capacity_kWh=20)
                         ),
                ],
            ),
            Area(
                'House 2',
                [
                    Area('Green Load 1', strategy=LoadHoursExternalStrategy(
                        avg_power_W=200, hrs_per_day=24, hrs_of_day=list(range(0, 24)),
                        final_buying_rate=35)
                         ),
                    Area('Green Load 5', strategy=LoadHoursExternalStrategy(
                        avg_power_W=200, hrs_per_day=20, hrs_of_day=list(range(2, 22)),
                        final_buying_rate=35)
                         ),
                    Area('Green PV 1', strategy=PVExternalStrategy(panel_count=4),
                         ),
                    Area('Green Storage 1', strategy=StorageExternalStrategy(initial_soc=50,
                                                                          min_allowed_soc=10,
                                                                          battery_capacity_kWh=5,
                                                                          max_abs_battery_power_kW=4)
                         ),

                ], external_connection_available=True,
            ),
            Area('Cell Tower', strategy=LoadHoursStrategy(avg_power_W=100,
                                                                   hrs_per_day=24,
                                                                   hrs_of_day=list(range(0, 24)),
                                                                   final_buying_rate=35)
                 ),
        ],
        config=config
    )
    return area

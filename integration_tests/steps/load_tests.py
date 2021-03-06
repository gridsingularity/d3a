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
from behave import then
from math import isclose

from d3a.setup.strategy_tests import user_profile_load_csv  # NOQA
from d3a.setup.strategy_tests import user_profile_load_csv_multiday  # NOQA
from d3a_interface.sim_results.export_unmatched_loads import MarketUnmatchedLoads, \
    get_number_of_unmatched_loads
from d3a.constants import FLOATING_POINT_TOLERANCE
from d3a.d3a_core.util import convert_W_to_Wh


@then('the DefinedLoadStrategy follows the {single_or_multi} day Load profile provided as csv')
def check_load_profile_csv(context, single_or_multi):
    from d3a.models.read_user_profile import read_arbitrary_profile, InputProfileTypes
    from d3a.d3a_core.util import find_object_of_same_weekday_and_time
    house1 = next(filter(lambda x: x.name == "House 1", context.simulation.area.children))
    load = next(filter(lambda x: x.name == "H1 DefinedLoad", house1.children))
    if single_or_multi == "single":
        path = user_profile_load_csv.profile_path
    else:
        path = user_profile_load_csv_multiday.profile_path
    input_profile = read_arbitrary_profile(InputProfileTypes.POWER, path)
    for timepoint, energy in load.strategy.state._desired_energy_Wh.items():
        assert energy == find_object_of_same_weekday_and_time(input_profile, timepoint) * 1000


@then('load only accepted offers lower than final_buying_rate')
def check_traded_energy_rate(context):
    house = next(filter(lambda x: x.name == "House 1", context.simulation.area.children))
    load = next(filter(lambda x: "H1 DefinedLoad" in x.name, house.children))

    for market in house.past_markets:
        for trade in market.trades:
            if trade.buyer == load.name:
                assert (trade.offer.price / trade.offer.energy) < \
                       load.strategy.bid_update.final_rate[market.time_slot]


@then('the DefinedLoadStrategy follows the Load profile provided as dict')
def check_user_pv_dict_profile(context):
    house = next(filter(lambda x: x.name == "House 1", context.simulation.area.children))
    load = next(filter(lambda x: x.name == "H1 DefinedLoad", house.children))
    from d3a.setup.strategy_tests.user_profile_load_dict import user_profile

    for market in house.past_markets:
        slot = market.time_slot
        if slot.hour in user_profile.keys():
            assert load.strategy.state._desired_energy_Wh[slot] == \
                   convert_W_to_Wh(user_profile[slot.hour], house.config.slot_length)
        else:
            if int(slot.hour) > int(list(user_profile.keys())[-1]):
                assert load.strategy.state._desired_energy_Wh[slot] == \
                       convert_W_to_Wh(user_profile[list(user_profile.keys())[-1]],
                                       house.config.slot_length)
            else:
                assert load.strategy.state._desired_energy_Wh[slot] == 0


@then('LoadHoursStrategy does not buy energy with rates that are higher than the provided profile')
def check_user_rate_profile_dict(context):
    house = next(filter(lambda x: x.name == "House 1", context.simulation.area.children))
    from integration_tests.steps.integration_tests import get_simulation_raw_results
    get_simulation_raw_results(context)
    count = 0
    unmatched = MarketUnmatchedLoads()
    for time_slot, core_stats in context.raw_sim_data.items():
        unmatched.update_unmatched_loads(
            context.area_tree_summary_data, core_stats, time_slot
        )
        unmatched_data, _ = unmatched.export_unmatched_loads.get_current_market_results(
            context.area_tree_summary_data, core_stats, time_slot
        )
        count += get_number_of_unmatched_loads(unmatched_data)
    # There are two loads with the same final_buying_rate profile that should report unmatched
    # energy demand for the first 6 hours of the day:
    number_of_loads = 2
    assert count == int(number_of_loads * 6. * 60 / house.config.slot_length.minutes)


@then('LoadHoursStrategy buys energy with rates equal to the initial buying rate profile')
def check_min_user_rate_profile_dict(context):
    house = next(filter(lambda x: x.name == "House 1", context.simulation.area.children))
    load1 = next(filter(lambda x: x.name == "H1 General Load 1", house.children))
    load2 = next(filter(lambda x: x.name == "H1 General Load 2", house.children))

    for market in house.past_markets:
        assert len(market.trades) > 0
        for trade in market.trades:
            trade_rate = trade.offer.price / trade.offer.energy
            if trade.buyer == load1.name:
                min_rate = load1.strategy.bid_update.initial_rate[market.time_slot]
                assert trade_rate - min_rate < FLOATING_POINT_TOLERANCE
            elif trade.buyer == load2.name:
                min_rate = load2.strategy.bid_update.initial_rate[market.time_slot]
                assert trade_rate - min_rate < FLOATING_POINT_TOLERANCE
            else:
                assert False, "All trades should be bought by load1 or load2, no other consumer."


@then('LoadHoursStrategy buys energy at the final_buying_rate')
def check_bid_update_frequency(context):
    for time_slot, core_stats in context.raw_sim_data.items():
        for trade in core_stats[context.name_uuid_map['House 1']]['trades']:
            if trade['buyer'] == 'H1 General Load':
                assert isclose(trade['energy_rate'], 35)
            else:
                assert False, "All trades should be bought by load1, no other consumer."

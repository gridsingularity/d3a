from d3a.d3a_core.util import area_name_from_area_or_iaa_name


def _is_cell_tower_type(area):
    return area['type'] == "CellTowerLoadHoursStrategy"


def _is_load_node_type(area):
    return area['type'] == "LoadHoursStrategy"


def _is_producer_node_type(area):
    return area['type'] in ["PVStrategy", "CommercialStrategy", "FinitePowerPlant",
                            "MarketMakerStrategy"]


def _is_prosumer_node_type(area):
    return area['type'] == "StorageStrategy"


def _is_buffer_node_type(area):
    return area['type'] == "InfiniteBusStrategy"


def area_sells_to_child(trade, area_name, child_names):
    return area_name_from_area_or_iaa_name(trade['seller']) == \
            area_name and area_name_from_area_or_iaa_name(trade['buyer']) in child_names


def child_buys_from_area(trade, area_name, child_names):
    return area_name_from_area_or_iaa_name(trade['buyer']) == \
        area_name and area_name_from_area_or_iaa_name(trade['seller']) in child_names
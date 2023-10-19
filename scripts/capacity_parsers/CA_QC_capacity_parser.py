from datetime import datetime

import pandas as pd
from bs4 import BeautifulSoup
from requests import Response, Session

from electricitymap.contrib.config import ZoneKey
from scripts.utils import convert_datetime_str_to_isoformat, update_zone

"""Disclaimer: only valid for real-time data, historical capacity is not available"""

MODE_MAPPING = {
    "Run-of-river": "hydro",
    "Reservoir": "hydro",
    "Gas-fired turbines": "gas",
    "Diesel": "oil",
    "Churchill Falls generating station â\x80\x94 Churchill Falls (Labrador) Corporation Limiteda": "hydro",
    "39\xa0wind farms operated by independent power producersb": "wind",
    "7\xa0biomass and 3\xa0biogas cogeneration plants operated by independent power producersc": "biomass",
    "5\xa0small hydropower plants operated by independent power producersb": "hydro",
    "Other suppliersd": "unknown",
}


def get_capacity_data():
    r: Response = Session().get(
        "https://www.hydroquebec.com/generation/generating-stations.html"
    )
    soup = BeautifulSoup(r.text, "html.parser")
    capacity = []

    capacity = []
    tables = soup.find_all("table")
    for table in tables:
        all_rows = table.find_all("tr")
        table_headers = [th.string for th in all_rows[0].find_all("th")]

        for row in all_rows:
            if len(row.find_all("td")):
                td = row.find_all("td")
                if "Watersheds" in table_headers:
                    pp_capacity = {
                        "mode": td[3].string,
                        "value": int(td[4].string.replace(",", "")),
                    }
                else:
                    pp_capacity = {
                        "mode": td[1].string,
                        "value": int(td[2].string.replace(",", "")),
                    }
                capacity.append(pp_capacity)

    table_others = soup.find_all("ul", attrs={"class": "hq-liste-donnees"})[0]

    all_rows = table_others.find_all("li")
    for row in all_rows[1:]:
        pp_capacity = {
            "mode": row.find("span", attrs={"class": "txt"}).text.strip(),
            "value": int(
                row.find("span", attrs={"class": "nbr"}).string[:-3].replace(",", "")
            ),
        }
        capacity.append(pp_capacity)

    df_capacity = pd.DataFrame(capacity)
    df_capacity["mode"] = df_capacity["mode"].map(MODE_MAPPING)
    df_capacity = df_capacity.groupby("mode")[["value"]].sum().reset_index()
    capacity_dict = {}
    for idx, data in df_capacity.iterrows():
        capacity_dict[data["mode"]] = {
            "datetime": datetime.now().strftime("%Y-01-01"),
            "value": data["value"],
            "source": "hydroquebec.com",
        }
    return capacity_dict


def get_and_update_capacity_for_one_zone(
    zone_key: ZoneKey, target_datetime: str
) -> None:
    target_datetime = convert_datetime_str_to_isoformat(target_datetime)
    zone_capacity = get_capacity_data()
    update_zone(zone_key, zone_capacity)
    print(f"Updated capacity for {zone_key} on {target_datetime.date()}")


if __name__ == "__main__":
    print(get_capacity_data())

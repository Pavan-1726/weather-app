import os
import sys
from dotenv import load_dotenv
import requests
from datetime import datetime

# ----------------------------------------------------------------------
# Configuration
load_dotenv()

# ----------------------------------------------------------------------
API_KEY = os.getenv("OPENWEATHER_API_KEY")
BASE_URL = "https://api.openweathermap.org/data/2.5"
GEO_URL = "https://api.openweathermap.org/geo/1.0/direct"


class WeatherApp:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError(
                "No API key found. Set the OPENWEATHER_API_KEY environment "
                "variable or edit API_KEY in the script."
            )
        self.api_key = api_key

    def get_coordinates(self, city: str, country_code: str = ""):
        """Convert a city name into latitude/longitude using the Geocoding API."""
        query = f"{city},{country_code}" if country_code else city
        params = {"q": query, "limit": 1, "appid": self.api_key}
        response = requests.get(GEO_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data:
            raise ValueError(f"City '{city}' not found.")

        return {
            "lat": data[0]["lat"],
            "lon": data[0]["lon"],
            "name": data[0]["name"],
            "country": data[0].get("country", ""),
        }

    def get_current_weather(self, city: str, units: str = "metric"):
        """Fetch current weather for a given city."""
        location = self.get_coordinates(city)
        params = {
            "lat": location["lat"],
            "lon": location["lon"],
            "appid": self.api_key,
            "units": units,
        }
        response = requests.get(f"{BASE_URL}/weather", params=params, timeout=10)
        response.raise_for_status()
        return response.json(), location

    def get_forecast(self, city: str, units: str = "metric"):
        """Fetch a 5-day / 3-hour forecast for a given city."""
        location = self.get_coordinates(city)
        params = {
            "lat": location["lat"],
            "lon": location["lon"],
            "appid": self.api_key,
            "units": units,
        }
        response = requests.get(f"{BASE_URL}/forecast", params=params, timeout=10)
        response.raise_for_status()
        return response.json(), location

    @staticmethod
    def format_current(data: dict, location: dict, units: str) -> str:
        symbol = "°C" if units == "metric" else "°F" if units == "imperial" else "K"
        speed_unit = "m/s" if units == "metric" else "mph" if units == "imperial" else "m/s"

        main = data["main"]
        weather = data["weather"][0]
        wind = data.get("wind", {})
        sys_info = data.get("sys", {})

        sunrise = datetime.fromtimestamp(sys_info.get("sunrise", 0)).strftime("%H:%M") if sys_info.get("sunrise") else "N/A"
        sunset = datetime.fromtimestamp(sys_info.get("sunset", 0)).strftime("%H:%M") if sys_info.get("sunset") else "N/A"

        lines = [
            f"\nWeather in {location['name']}, {location['country']}",
            "-" * 45,
            f"Condition:     {weather['main']} ({weather['description']})",
            f"Temperature:   {main['temp']}{symbol} (feels like {main['feels_like']}{symbol})",
            f"Min / Max:     {main['temp_min']}{symbol} / {main['temp_max']}{symbol}",
            f"Humidity:      {main['humidity']}%",
            f"Pressure:      {main['pressure']} hPa",
            f"Wind:          {wind.get('speed', 'N/A')} {speed_unit}",
            f"Cloudiness:    {data.get('clouds', {}).get('all', 'N/A')}%",
            f"Sunrise:       {sunrise}",
            f"Sunset:        {sunset}",
            "-" * 45,
        ]
        return "\n".join(lines)

    @staticmethod
    def format_forecast(data: dict, location: dict, units: str, days: int = 5) -> str:
        symbol = "°C" if units == "metric" else "°F" if units == "imperial" else "K"

        lines = [f"\n5-Day Forecast for {location['name']}, {location['country']}", "-" * 45]

        seen_dates = set()
        count = 0
        for entry in data["list"]:
            dt = datetime.fromtimestamp(entry["dt"])
            date_str = dt.strftime("%Y-%m-%d")

            # Take one reading per day (around midday) to keep it concise
            if date_str in seen_dates:
                continue
            if dt.hour < 11 or dt.hour > 14:
                continue

            seen_dates.add(date_str)
            count += 1

            weather = entry["weather"][0]
            temp = entry["main"]["temp"]
            lines.append(
                f"{dt.strftime('%a %d %b'):<12} {weather['description']:<20} {temp:>6.1f}{symbol}"
            )

            if count >= days:
                break

        lines.append("-" * 45)
        return "\n".join(lines)


def main():
    print("=" * 45)
    print("        PYTHON WEATHER APPLICATION")
    print("=" * 45)

    try:
        app = WeatherApp(API_KEY)
    except ValueError as e:
        print(f"\nSetup error: {e}")
        sys.exit(1)

    while True:
        print("\nOptions:")
        print("  1. Current weather")
        print("  2. 5-day forecast")
        print("  3. Change units")
        print("  4. Quit")

        choice = input("\nSelect an option (1-4): ").strip()

        if choice == "4" or choice.lower() == "q":
            print("Goodbye!")
            break

        elif choice == "3":
            units = input("Units - metric (C) / imperial (F) / standard (K): ").strip().lower()
            if units not in ("metric", "imperial", "standard"):
                print("Invalid unit, defaulting to metric.")
                units = "metric"
            globals()["CURRENT_UNITS"] = units
            print(f"Units set to: {units}")
            continue

        elif choice in ("1", "2"):
            city = input("Enter city name: ").strip()
            if not city:
                print("City name cannot be empty.")
                continue

            units = globals().get("CURRENT_UNITS", "metric")

            try:
                if choice == "1":
                    data, location = app.get_current_weather(city, units)
                    print(app.format_current(data, location, units))
                else:
                    data, location = app.get_forecast(city, units)
                    print(app.format_forecast(data, location, units))

            except ValueError as e:
                print(f"\nError: {e}")
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 401:
                    print("\nError: Invalid API key. Check your OPENWEATHER_API_KEY.")
                elif e.response.status_code == 404:
                    print(f"\nError: City '{city}' not found.")
                else:
                    print(f"\nHTTP error: {e}")
            except requests.exceptions.RequestException as e:
                print(f"\nNetwork error: {e}")

        else:
            print("Invalid option, please choose 1-4.")


if __name__ == "__main__":
    main()

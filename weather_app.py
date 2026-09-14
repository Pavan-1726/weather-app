import os
import sys
from dotenv import load_dotenv
import requests
from datetime import datetime
from flask import Flask, jsonify, render_template_string, request

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


WEB_PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Atmos Weather</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">
  <style>
    :root{--ink:#152432;--muted:#61717b;--paper:#f5f7f3;--line:#dce5e2;--teal:#0d7375;--sun:#f1a348;--white:#fff}*{box-sizing:border-box}body{margin:0;color:var(--ink);background:var(--paper);font-family:'DM Sans',sans-serif}main{max-width:1160px;margin:auto;padding:30px 24px 56px}header{display:flex;justify-content:space-between;align-items:center;margin-bottom:54px}.brand{font:700 25px 'Space Grotesk';letter-spacing:-1px}.brand span{color:var(--teal)}.unit-toggle{display:flex;border:1px solid var(--line);border-radius:7px;padding:3px;background:var(--white)}button{border:0;cursor:pointer;font:500 14px 'DM Sans'}.unit{padding:8px 12px;border-radius:5px;color:var(--muted);background:transparent}.unit.active{color:var(--white);background:var(--ink)}.intro{display:grid;grid-template-columns:1fr 1.05fr;gap:64px;align-items:end;margin-bottom:38px}h1{max-width:560px;margin:0;font:600 clamp(42px,6vw,76px)/.98 'Space Grotesk';letter-spacing:-3px}.intro p{max-width:390px;margin:18px 0 0;color:var(--muted);line-height:1.6}form{display:flex;gap:10px;border-bottom:2px solid var(--ink);padding-bottom:10px}input{min-width:0;flex:1;border:0;outline:0;color:var(--ink);background:transparent;font:500 20px 'Space Grotesk'}input::placeholder{color:#aab5b5}.search{width:46px;height:40px;border-radius:5px;color:var(--white);background:var(--teal);font-size:20px}#message{min-height:24px;margin:16px 0;color:#b44e3d}.dashboard{display:none}.dashboard.visible{display:block;animation:rise .45s ease both}.current{display:grid;grid-template-columns:1.2fr .8fr;gap:20px;padding:30px;color:var(--white);background:var(--teal);border-radius:8px}.eyebrow{margin:0 0 8px;color:#acd9d3;font-size:13px;letter-spacing:1.2px;text-transform:uppercase}.place{margin:0;font:600 38px 'Space Grotesk';letter-spacing:-1.5px}.date{margin:7px 0 0;color:#c4e4de}.temperature{align-self:center;font:600 78px/.9 'Space Grotesk';letter-spacing:-5px;text-align:right}.temperature small{font-size:26px;letter-spacing:0;vertical-align:top}.condition{align-self:end;color:#d7eeea;text-transform:capitalize}.metrics{display:grid;grid-template-columns:repeat(4,1fr);border-bottom:1px solid var(--line)}.metric{padding:22px 14px 22px 0}.metric+.metric{padding-left:22px;border-left:1px solid var(--line)}.metric label{display:block;margin-bottom:7px;color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:1px}.metric strong{font:600 20px 'Space Grotesk'}.forecast-head{margin:36px 0 15px}h2{margin:0;font:600 26px 'Space Grotesk'}.forecast{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}.day{min-height:155px;display:flex;flex-direction:column;justify-content:space-between;padding:17px;border:1px solid var(--line);border-radius:7px;background:var(--white)}.day-date,.day-desc{color:var(--muted);font-size:13px}.day-icon{color:var(--sun);font-size:27px}.day-temp{font:600 24px 'Space Grotesk'}.day-desc{text-transform:capitalize}@keyframes rise{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}@media(max-width:700px){main{padding:22px 18px 40px}header{margin-bottom:42px}.intro{display:block}.intro p{margin-bottom:30px}.current{grid-template-columns:1fr 1fr;padding:22px}.place{font-size:29px}.temperature{font-size:58px}.metrics{grid-template-columns:repeat(2,1fr)}.metric+.metric{padding-left:14px;border-left:0}.metric:nth-child(even){padding-left:14px;border-left:1px solid var(--line)}.forecast{grid-template-columns:repeat(2,1fr)}}
  </style>
</head>
<body><main>
  <header><div class="brand">atmos<span>.</span></div><div class="unit-toggle"><button class="unit active" data-unit="metric">°C</button><button class="unit" data-unit="imperial">°F</button></div></header>
  <section class="intro"><div><h1>Weather,<br>with clarity.</h1><p>Simple, considered forecasts for wherever you are headed next.</p></div><form id="search-form"><input id="city" placeholder="Search a city..." autocomplete="off" required><button class="search" aria-label="Search">→</button></form></section>
  <div id="message">Search for a city to see the latest conditions.</div>
  <section id="dashboard" class="dashboard"><div class="current"><div><p class="eyebrow">Current conditions</p><h2 id="place" class="place"></h2><p id="date" class="date"></p></div><div><div id="temperature" class="temperature"></div><div id="condition" class="condition"></div></div></div><div class="metrics"><div class="metric"><label>Feels like</label><strong id="feels"></strong></div><div class="metric"><label>Humidity</label><strong id="humidity"></strong></div><div class="metric"><label>Wind</label><strong id="wind"></strong></div><div class="metric"><label>Sunrise / sunset</label><strong id="sun"></strong></div></div><div class="forecast-head"><h2>Five day outlook</h2></div><div id="forecast" class="forecast"></div></section>
</main><script>
let unit='metric';const $=id=>document.getElementById(id);const icon=main=>({Clear:'○',Clouds:'☁',Rain:'☂',Drizzle:'☂',Snow:'✣',Thunderstorm:'ϟ'}[main]||'○');document.querySelectorAll('.unit').forEach(button=>button.addEventListener('click',()=>{unit=button.dataset.unit;document.querySelectorAll('.unit').forEach(item=>item.classList.remove('active'));button.classList.add('active');if($('city').value)loadWeather($('city').value)}));$('search-form').addEventListener('submit',event=>{event.preventDefault();loadWeather($('city').value)});async function loadWeather(city){$('message').textContent='Reading the sky...';$('dashboard').classList.remove('visible');try{const response=await fetch(`/api/weather?city=${encodeURIComponent(city)}&units=${unit}`);const result=await response.json();if(!response.ok)throw new Error(result.error||'Could not load weather.');const{current,location,forecast}=result;const symbol=unit==='metric'?'°C':'°F';$('place').textContent=`${location.name}, ${location.country}`;$('date').textContent=new Date().toLocaleDateString(undefined,{weekday:'long',month:'long',day:'numeric'});$('temperature').innerHTML=`${Math.round(current.main.temp)}<small>${symbol}</small>`;$('condition').textContent=current.weather[0].description;$('feels').textContent=`${Math.round(current.main.feels_like)}${symbol}`;$('humidity').textContent=`${current.main.humidity}%`;$('wind').textContent=`${current.wind?.speed??'N/A'} ${unit==='metric'?'m/s':'mph'}`;$('sun').textContent=`${formatTime(current.sys.sunrise)} / ${formatTime(current.sys.sunset)}`;$('forecast').innerHTML=forecast.map(day=>`<article class="day"><span class="day-date">${day.date}</span><span class="day-icon">${icon(day.main)}</span><strong class="day-temp">${Math.round(day.temp)}${symbol}</strong><span class="day-desc">${day.description}</span></article>`).join('');$('message').textContent='';$('dashboard').classList.add('visible')}catch(error){$('message').textContent=error.message}}function formatTime(timestamp){return timestamp?new Date(timestamp*1000).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'}):'N/A'}
</script></body></html>
"""


def create_web_app(weather_app):
    web_app = Flask(__name__)

    @web_app.get("/")
    def index():
        return render_template_string(WEB_PAGE)

    @web_app.get("/api/weather")
    def weather():
        city = request.args.get("city", "").strip()
        units = request.args.get("units", "metric")
        if not city:
            return jsonify(error="Enter a city name."), 400
        if units not in ("metric", "imperial", "standard"):
            units = "metric"
        try:
            current, location = weather_app.get_current_weather(city, units)
            forecast_data, _ = weather_app.get_forecast(city, units)
            forecast = []
            seen_dates = set()
            for entry in forecast_data["list"]:
                date = datetime.fromtimestamp(entry["dt"]).strftime("%a %d %b")
                if date in seen_dates:
                    continue
                seen_dates.add(date)
                forecast.append({"date": date, "main": entry["weather"][0]["main"], "description": entry["weather"][0]["description"], "temp": entry["main"]["temp"]})
                if len(forecast) == 5:
                    break
            return jsonify(current=current, location=location, forecast=forecast)
        except ValueError as error:
            return jsonify(error=str(error)), 404
        except requests.exceptions.HTTPError as error:
            status = error.response.status_code if error.response is not None else 502
            message = "Invalid API key." if status == 401 else f"Could not find weather for '{city}'." if status == 404 else "Weather service error."
            return jsonify(error=message), status
        except requests.exceptions.RequestException:
            return jsonify(error="The weather service is unavailable right now."), 503

    return web_app


def create_server():
    return create_web_app(WeatherApp(API_KEY))


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
    try:
        app = WeatherApp(API_KEY)
    except ValueError as error:
        print(f"Setup error: {error}")
        sys.exit(1)

    if "--cli" in sys.argv:
        main()
    else:
        create_web_app(app).run(debug=True)

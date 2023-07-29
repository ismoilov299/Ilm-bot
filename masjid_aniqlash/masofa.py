import urllib.parse

def show(lat, lon, name):
    encoded_name = urllib.parse.quote(name)
    url = f"http://maps.google.com/maps?q={lat},{lon}&q={encoded_name}"
    return url

import streamlit as st
import pandas as pd
import folium
import math
import random
import requests
import geocoder
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation
from datetime import datetime

# 1. SAYFA AYARLARI (En üstte tek bir tane olmalı)
st.set_page_config(page_title="EV Karar Destek", layout="wide")

# --- 2. FONKSİYONLAR ---
def konumu_otomatik_bul():
    try:
        g = geocoder.ip('me')
        return g.city if g.city else "Bilecik"
    except:
        return "Bilecik"

def sicaklik_getir(sehir_adi):
    api_key = "5ea92f3cce5b21df053a6fa7f31fd0e5"
    if sehir_adi == "Mevcut Konumunuz": return 18.5
    url = f"http://api.openweathermap.org/data/2.5/weather?q={sehir_adi.strip()}&appid={api_key}&units=metric"
    try:
        response = requests.get(url).json()
        if response.get("cod") == 200: return response['main']['temp']
        return 15.0
    except:
        return 12.0

def trafik_durumu_simule_et():
    saat = datetime.now().hour
    if (8 <= saat <= 9) or (17 <= saat <= 19): return random.randint(70, 95)
    return random.randint(20, 50)

# --- 3. ANA PANEL VE SIDEBAR ---
st.title("⚡ Akıllı Elektrikli Araç Şarj İstasyonu Paneli")
st.sidebar.header("Araç ve Konum Bilgileri")

sehir_merkezleri = {
    "Bilecik": [40.1425, 29.9795], "Kütahya": [39.4200, 29.9850], "Eskişehir": [39.7767, 30.5206],
    "Bursa": [40.1885, 29.0610], "İstanbul": [41.0082, 28.9784], "Ankara": [39.9334, 32.8597]
}

# GPS YÖNETİMİ
loc_data = get_geolocation()

if loc_data and loc_data.get('coords'):
    enlem = loc_data['coords']['latitude']
    boylam = loc_data['coords']['longitude']
    merkez = [enlem, boylam]
    st.sidebar.success(f"✅ GPS Bağlandı: {round(enlem,4)}, {round(boylam,4)}")
    temiz_sehir = "Mevcut Konumunuz"
else:
    otomatik_sehir = konumu_otomatik_bul()
    temiz_sehir = otomatik_sehir.strip().title()
    merkez = sehir_merkezleri.get(temiz_sehir, [40.1885, 29.0610])
    if loc_data is None:
        st.sidebar.warning("📡 Hassas konum için GPS izni bekleniyor...")
    else:
        st.sidebar.info(f"🌐 Şehir Tahmini: {temiz_sehir}")

# VERİ GİRİŞLERİ
sicaklik = sicaklik_getir(temiz_sehir)
arac = st.sidebar.selectbox("Aracınız", ["Togg T10X", "Tesla Model Y", "Fiat 500e"])
mevcut_sarj = st.sidebar.slider("Mevcut Şarj (%)", 0, 100, 40)
otomatik_trafik = trafik_durumu_simule_et()
mevcut_trafik = st.sidebar.slider("Mevcut Trafik (%)", 0, 100, otomatik_trafik)

if mevcut_trafik > 70:
    st.sidebar.error("🔴 Yoğun Trafik: Menzil %20 azalıyor!")
else:
    st.sidebar.success("🟢 Trafik Akıcı.")
st.sidebar.info(f"🌡️ Anlık Sıcaklık: {sicaklik}°C")

# --- 4. HESAPLAMALAR VE METRİKLER ---
menzil_katsayisi = 0.8 if sicaklik < 5 else 1.0
trafik_etkisi = 0.8 if mevcut_trafik > 70 else 1.0
tahmini_menzil = (mevcut_sarj * 4) * menzil_katsayisi * trafik_etkisi

col1, col2, col3 = st.columns(3)
col1.metric("Tahmini Kalan Menzil", f"{round(tahmini_menzil, 1)} km")
col2.metric("Hava Durumu", f"{sicaklik} °C")
col3.metric("Sistem Verimliliği", f"%{int(menzil_katsayisi * 100)}")

# --- 5. ÖNERİ SİSTEMİ ---
st.markdown("---")
oneri_sehri = "Bilecik" if temiz_sehir == "Mevcut Konumunuz" else temiz_sehir
istasyon_onerileri = {
    "Bilecik": "Trugo (Hükümet Meydanı)", "Kütahya": "ZES (Lalin Garden)",
    "Eskişehir": "Eşarj (Espark AVM)", "Bursa": "Trugo (Togg Gemlik Tesisi)",
    "Ankara": "Eşarj (Armada AVM)", "İstanbul": "ZES (Zorlu Center)"
}
onerilen_istasyon = istasyon_onerileri.get(oneri_sehri, "En yakın yüksek hızlı DC istasyonu")

if tahmini_menzil < 50:
    st.error(f"⚠️ **Menzil Kritik!** Kalan: {round(tahmini_menzil, 1)} km.")
    st.info(f"💡 **Öneri:** {oneri_sehri} sınırlarındaki **{onerilen_istasyon}** noktasına gidin.")
elif tahmini_menzil < 120:
    st.warning(f"🔔 **Dikkat:** Menzil azalıyor. **{onerilen_istasyon}** üzerinden geçmeniz rasyonel olur.")
else:
    st.success(f"✅ **Yolculuk Güvenli:** Mevcut menzil yeterli. Şarj gerekirse **{onerilen_istasyon}** en iyi seçenektir.")

# --- 6. HARİTA VE İSTASYONLAR ---
istasyon_verileri = {
    "Bilecik": pd.DataFrame({'ad': ['Trugo', 'Eşarj', 'ZES'], 'lat': [40.142, 40.145, 40.150], 'lon': [29.979, 29.975, 29.985]}),
    "Kütahya": pd.DataFrame({'ad': ['ZES (Lalin)', 'Eşarj (Vazo)'], 'lat': [39.421, 39.418], 'lon': [29.986, 29.982]}),
    "Bursa": pd.DataFrame({'ad': ['Trugo (Gemlik)', 'ZES (Podyum)'], 'lat': [40.428, 40.222], 'lon': [29.155, 28.995]}),
    "Eskişehir": pd.DataFrame({'ad': ['Eşarj (Espark)', 'ZES'], 'lat': [39.776, 39.780], 'lon': [30.520, 30.530]})
}

# En yakın ili bul
if loc_data and loc_data.get('coords'):
    lat_gps, lon_gps = loc_data['coords']['latitude'], loc_data['coords']['longitude']
    en_yakin_il, min_d = "Bilecik", float('inf')
    for sehir, koord in sehir_merkezleri.items():
        d = math.sqrt((lat_gps - koord[0])**2 + (lon_gps - koord[1])**2)
        if d < min_d: min_d, en_yakin_il = d, sehir
    aktif_sehir = en_yakin_il if temiz_sehir == "Mevcut Konumunuz" else temiz_sehir
else:
    aktif_sehir = temiz_sehir

st.subheader(f"📍 {aktif_sehir} Yakınındaki Şarj İstasyonları")

# HARİTA OBJESİNİ BAŞLAT (Kritik eksik buradaydı)
m = folium.Map(location=merkez, zoom_start=14)

# Mavi İkon (Senin Konumun)
folium.Marker(location=merkez, popup="Şu an buradasınız", icon=folium.Icon(color='blue', icon='user', prefix='fa')).add_to(m)

# İstasyonları Ekle
df_istasyon = istasyon_verileri.get(aktif_sehir, pd.DataFrame(columns=['ad', 'lat', 'lon']))
for i, row in df_istasyon.iterrows():
    R = 6371
    lat1, lon1, lat2, lon2 = map(math.radians, [merkez[0], merkez[1], row['lat'], row['lon']])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    mesafe = round(R * c, 2)
    
    doluluk = random.randint(10, 95)
    renk = 'red' if doluluk > 80 else ('orange' if doluluk > 50 else 'green')
    folium.Marker(
        [row['lat'], row['lon']],
        popup=f"<b>{row['ad']}</b><br>Uzaklık: {mesafe} km<br>Doluluk: %{doluluk}",
        icon=folium.Icon(color=renk, icon='bolt', prefix='fa')
    ).add_to(m)

# HARİTAYI ÇİZ
st_folium(m, width=1000, height=500, key="harita_final", returned_objects=[])
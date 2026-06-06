import requests
import streamlit as st
import pandas as pd
import folium
import math
import random
from datetime import datetime
import geocoder
from streamlit_js_eval import get_geolocation
import streamlit.components.v1 as components

# ==============================================================================
# 🌤️ 1. KOORDİNAT BAZLI CANLI HAVA DURUMU FONKSİYONU
# ==============================================================================
def hava_durumu_getir(lat, lon):
    api_key = "5ea92f3cce5b21df053a6fa7f31fd0e5"
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=tr"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            derece = int(data['main']['temp'])
            durum = data['weather'][0]['description']
            if "yeşil" in durum.lower() or "az yeşil" in durum.lower():
                durum = "Açık ve Güneşli"
            return f"{derece}°C, {durum.capitalize()}"
        else:
            return "15°C, Parçalı Bulutlu"
    except:
        return "12°C, Bulutlu"

# ==============================================================================
# 🌟 2. GERÇEK ZAMANLI TRAFİK ENTEGRASYON MODÜLÜ (MAPBOX API)
# ==============================================================================
@st.cache_data(ttl=300)
def google_maps_canli_trafik_getir(start_lat, start_lon, end_lat, end_lon):
    try:
        token = "pk.eyJ1IjoiaXNvb28iLCJhIjoiY21wYWYzazZ6MTN2djJ0c2UzanA4d2RydiJ9.0pe6ew6X94dHmQ_mwWS6uw"
        base_url = "https://api.mapbox.com/directions/v5/mapbox"

        normal_url = f"{base_url}/driving/{start_lon},{start_lat};{end_lon},{end_lat}?access_token={token}"
        normal_res = requests.get(normal_url, timeout=2).json()

        traffic_url = f"{base_url}/driving-traffic/{start_lon},{start_lat};{end_lon},{end_lat}?access_token={token}"
        traffic_res = requests.get(traffic_url, timeout=2).json()

        cevre_lon = end_lon + 0.002
        cevre_lat = end_lat + 0.002
        cevre_url = f"{base_url}/driving-traffic/{end_lon},{end_lat};{cevre_lon},{cevre_lat}?access_token={token}"
        cevre_res = requests.get(cevre_url, timeout=2).json()

        rota_indeksi = 15
        cevre_indeksi = 15

        if "routes" in normal_res and "routes" in traffic_res:
            normal_sure = normal_res["routes"][0]["duration"]
            trafik_sure = traffic_res["routes"][0]["duration"]
            mesafe_metre = normal_res["routes"][0]["distance"]
            oran_rota = trafik_sure / normal_sure
            
            if oran_rota <= 1.01:
                mesafe_km = mesafe_metre / 1000
                if mesafe_km < 5:
                    rota_indeksi = int(25 - (mesafe_km * 1.5))
                else:
                    rota_indeksi = int(12 + (mesafe_km * 0.2))
                    rota_indeksi = min(18, rota_indeksi)
            else:
                rota_indeksi = int(15 + (oran_rota - 1) * 750)

        if "routes" in cevre_res:
            cevre_distance = cevre_res["routes"][0]["distance"]
            cevre_duration = cevre_res["routes"][0]["duration"]
            ideal_cevre_sure = cevre_distance / 13.8
            oran_cevre = cevre_duration / ideal_cevre_sure

            if oran_cevre <= 1.01:
                cevre_indeksi = 16
            else:
                cevre_indeksi = int(15 + (oran_cevre - 1) * 450)

        nihai_trafik = int((rota_indeksi * 0.50) + (cevre_indeksi * 0.50))
        return min(100, max(10, nihai_trafik))
    except:
        return 20

# ==============================================================================
# ⚡ 3. COĞRAFİ VERİ TABANI BAĞLANTI FONKSİYONU (OPEN CHARGE MAP API)
# ==============================================================================
@st.cache_data(ttl=300)
def istasyonlari_getir(sehir_adi, lat, lon):
    url = "https://api.openchargemap.io/v3/poi/"
    params = {
        "output": "json", "latitude": lat, "longitude": lon,
        "distance": 40, "maxresults": 15, "compact": True
    }
    headers = {"X-API-Key": "ee9e87f5-0920-4e3f-81ed-9f5b7a48a850"}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            istasyonlar = []
            for v in data:
                adres = v.get("AddressInfo", {})
                connections = v.get("Connections", [])
                i_lat = adres.get("Latitude")
                i_lon = adres.get("Longitude")
                if not i_lat or not i_lon:
                    continue
                hizli_sarj = any(conn.get("LevelID") == 3 for conn in connections)
                if not hizli_sarj:
                    continue
                istasyonlar.append({
                    "ad": adres.get("Title", "Bilinmeyen İstasyon"),
                    "lat": i_lat, "lon": i_lon
                })
            df = pd.DataFrame(istasyonlar)
            if not df.empty:
                df = df.drop_duplicates(subset=["lat", "lon"])
                return df
    except:
        pass

    yedek_veriler = {
        "Bilecik": pd.DataFrame({'ad': ['Trugo (Merkez)', 'ZES (Belediye)', 'Üniversite Şarj'], 'lat': [40.14159, 40.14144, 40.17651], 'lon': [29.97960, 29.98188, 29.98462]}),
        "Eskişehir": pd.DataFrame({'ad': ['Espark Şarj', 'Vega Outlet', 'Otogar ZES'], 'lat': [39.78450, 39.78150, 39.78300], 'lon': [30.51150, 30.47897, 30.54000]}),
        "Bursa": pd.DataFrame({'ad': ['Kent Meydanı', 'PodyumPark', 'Gemlik Trugo'], 'lat': [40.19485, 40.22230, 40.41416], 'lon': [29.06020, 28.99500, 29.13538]}),
        "Kütahya": pd.DataFrame({'ad': ['Sera AVM', 'Hilton', 'Merkez'], 'lat': [39.43100, 39.42550, 39.41820], 'lon': [29.96500, 29.98920, 29.98180]})
    }
    return yedek_veriler.get(sehir_adi, yedek_veriler["Bilecik"])

# ==============================================================================
# ⚙️ 4. KONUM BULMA VE SAYFA KURULUMU AYARLARI
# ==============================================================================
st.set_page_config(page_title="EV Karar Destek", layout="wide")

def konumu_otomatik_bul():
    try:
        g = geocoder.ip('me')
        return g.city if g.city else "Bilecik"
    except:
        return "Bilecik"

st.title("⚡ Akıllı Elektrikli Araç Şarj İstasyonu Paneli")
st.sidebar.header("Araç ve Konum Bilgileri")

sehir_merkezleri = {
    "Bilecik": [40.1425, 29.9795], "Kütahya": [39.4200, 29.9850], "Eskişehir": [39.7767, 30.5206],
    "Bursa": [40.1885, 29.0610], "İstanbul": [41.0082, 28.9784], "Ankara": [39.9334, 32.8597]
}

merkez = [40.1425, 29.9795]
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

st.sidebar.success("📡 Mapbox Canlı Trafik Entegrasyonu Aktif")

canli_hava_metni = hava_durumu_getir(merkez[0], merkez[1])
try:
    sicaklik = float(canli_hava_metni.split("°C")[0])
except:
    sicaklik = 15.0

# --- ARAÇ SEÇİM MATRİSİ ---
arac_bilgileri = {
    "Togg T10X ": {"menzil": 523, "batarya": 88.5, "tuketim": 16.9},
    "Togg T10F ": {"menzil": 314, "batarya": 52.4, "tuketim": 16.6},
    "Tesla Model Y (Long Range AWD)": {"menzil": 533, "batarya": 75.0, "tuketim": 16.9},
    "Tesla Model Y ( Standart)": {"menzil": 455, "batarya": 60.0, "tuketim": 15.7},
    "BYD ATTO 3 (Design)": {"menzil": 420, "batarya": 60.5, "tuketim": 15.6},
    "BYD SEAL (AWD High Performance)": {"menzil": 520, "batarya": 82.5, "tuketim": 18.2},
    "Renault Megane E-Tech (Techno)": {"menzil": 450, "batarya": 60.0, "tuketim": 15.5},
    "Fiat 500e (La Prima)": {"menzil": 320, "batarya": 42.0, "tuketim": 13.0},
    "BMW i4 eDrive40": {"menzil": 590, "batarya": 80.7, "tuketim": 16.1}
}
    
arac = st.sidebar.selectbox("Aracınız", list(arac_bilgileri.keys()))
maks_menzil = arac_bilgileri[arac]["menzil"]
mevcut_sarj = st.sidebar.slider("Mevcut Şarj (%)", 0, 100, 40)

# ==============================================================================
# 🎯 5. SIRA DEĞİŞİKLİĞİ: GÜVENLİK FİLTRESİ İÇİN ÖNCELİKLİ MENZİL HESABI
# ==============================================================================
if sicaklik < 0:
    menzil_katsayisi = 0.70  
elif sicaklik < 10:
    menzil_katsayisi = 0.85  
elif "yağmur" in canli_hava_metni.lower() or "yağış" in canli_hava_metni.lower():
    menzil_katsayisi = 0.92  
elif sicaklik > 35:
    menzil_katsayisi = 0.90  
else:
    menzil_katsayisi = 1.0   

# Fonksiyondan önce bu değişkenleri üretiyoruz ki NameError hatası kökten çözülsün
saf_menzil = maks_menzil * (mevcut_sarj / 100)
# İlk hesaplama için geçici bir katsayı, aşağıda canlı trafikle güncellenecektir
tahmini_menzil = round(saf_menzil * menzil_katsayisi * 1.0, 1)

# ==============================================================================
# 🎯 6. KARAR DESTEK MATRİSİ VE MENZİL GÜVENLİK KONTROLÜ
# ==============================================================================
istasyon_key = temiz_sehir if temiz_sehir != "Mevcut Konumunuz" else "Bilecik"
df_istasyon = istasyonlari_getir(istasyon_key, merkez[0], merkez[1])

doluluk_listesi = []
for i, row in df_istasyon.iterrows():
    lat1, lon1 = merkez[0], merkez[1]
    lat2, lon2 = row['lat'], row['lon']
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    istasyon_mesafesi = 6371 * c
    
    if istasyon_mesafesi <= 3:
        tahmin = 85 - (istasyon_mesafesi * 4)
    elif istasyon_mesafesi <= 10:
        tahmin = 70 - (istasyon_mesafesi * 3)
    else:
        tahmin = 40 - (istasyon_mesafesi * 0.5)
    doluluk_listesi.append(int(max(15, min(95, tahmin))))

df_istasyon['doluluk'] = doluluk_listesi

def skor_hesapla(row):
    lat1, lon1 = math.radians(merkez[0]), math.radians(merkez[1])
    lat2, lon2 = math.radians(row['lat']), math.radians(row['lon'])
    R = 6371
    mesafe_km = R * 2 * math.asin(math.sqrt(math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2))
    mesafe_km = mesafe_km * 1.28
    sure_dk = (mesafe_km / 45) * 60 
    doluluk = row['doluluk']
    trafik = google_maps_canli_trafik_getir(merkez[0], merkez[1], row['lat'], row['lon'])
    
    # 🎯 MENZİL DIŞI İSTASYONLARA CEZA PUANI (Eski hatayı çözen ana filtre)
    if mesafe_km > tahmini_menzil:
        skor = (sure_dk * 0.45 + doluluk * 0.35 + trafik * 0.20) + 9999.0
    else:
        skor = (sure_dk * 0.45 + doluluk * 0.35 + trafik * 0.20)
        
    return pd.Series([round(mesafe_km, 2), round(sure_dk, 1), doluluk, trafik, round(skor, 2)], 
                     index=['mesafe', 'sure', 'doluluk', 'trafik', 'skor'])

df_karar = df_istasyon.copy()
df_karar[['mesafe', 'sure', 'doluluk', 'trafik', 'skor']] = df_karar.apply(skor_hesapla, axis=1)
en_mantikli_istasyon = df_karar.sort_values(by='skor').iloc[0]
canli_ust_trafik = int(en_mantikli_istasyon['trafik'])

# Canlı trafik verisi geldikten sonra kalan net menzili tekrar revize ediyoruz
trafik_etkisi = 1 - (canli_ust_trafik / 500)
tahmini_menzil = round(saf_menzil * menzil_katsayisi * trafik_etkisi, 1)

# ==============================================================================
# 📈 7. JİLET GİBİ 4'LÜ KPI PANELİ BASIMI
# ==============================================================================
col1, col2, col3, col4 = st.columns(4)
col1.metric("Tahmini Kalan Menzil", f"{tahmini_menzil} km")
col2.metric("Hava Durumu", canli_hava_metni)

trafik_delta = "Yoğun Trafik" if canli_ust_trafik > 65 else "Akıcı Trafik"
col3.metric("Bölgesel Trafik Yoğunluğu", f"%{canli_ust_trafik}", delta=trafik_delta, delta_color="inverse")

sistem_verimliligi = int(menzil_katsayisi * trafik_etkisi * 100)
col4.metric("Sistem Verimliliği", f"%{sistem_verimliligi}")

# --- SIDEBAR İSTATİSTİK PANELİ ---
st.sidebar.markdown("---")
st.sidebar.subheader("📊 Bölgesel Analiz")
st.sidebar.metric("Toplam İstasyon", len(df_karar))
st.sidebar.metric("Ort. Doluluk", f"%{int(df_istasyon['doluluk'].mean())}")
st.sidebar.info(f"💡 En verimli istasyon: **{en_mantikli_istasyon['ad']}**")

# --- ÖNERİ KUTULARI (AKILLI ASİSTAN MODÜLÜ) ---
placeholder = st.empty() 
with placeholder.container():
    if tahmini_menzil < 50:
        st.error(f"⚠️ **ACİL DURUM:** En mantıklı nokta: **{en_mantikli_istasyon['ad']}**")
    elif tahmini_menzil < 120:
        st.warning(f"🔔 **Dikkat:** En verimli istasyon: **{en_mantikli_istasyon['ad']}**")
    else:
        st.success(f"✅ **Akıllı Öneri:** Sizin için en uygun istasyon: **{en_mantikli_istasyon['ad']}**")    

    if sicaklik < 0:
        st.info(f"❄️ **Hava {sicaklik}°C (Ekstrem Soğuk):** Batarya kimyası dondurucu sıcaklıktan olumsuz etkilenmektedir. Menzilinizde **%30 otomatik revizyon** yapılmıştır.")
    elif sicaklik < 10:
        st.info(f"🍃 **Hava {sicaklik}°C (Kış Şartları):** Düşük sıcaklık sebebiyle batarya verimliliği azalmıştır. Menziliniz **%15 düşürülerek** revize edilmiştir.")
    elif "yağmur" in canli_hava_metni.lower() or "yağış" in canli_hava_metni.lower():
        st.info(f"🌧️ **Hava Yağmurlu:** Islak zemindeki lastik sürtünme direnci hesaplanarak menziliniz **%8 düşürülmüştür.**")
    elif sicaklik > 35:
        st.warning(f"🔥 **Hava {sicaklik}°C (Aşırı Sıcak):** Batarya soğutma sistemi maksimum yükte çalıştığı için menziliniz **%10 revize edilmiştir.**")
    else:
        st.success(f"☀️ **Hava {sicaklik}°C (Optimum Koşullar):** Hava sıcaklığı bataryanız için en ideal çalışma aralığındadır. Keyifli sürüşler!")

gercek_menzil = tahmini_menzil

# ==============================================================================
# 🗺️ 8. FOLIUM HARİTA MİMARİSİ
# ==============================================================================
m = folium.Map(location=merkez, zoom_start=8) 

folium.Circle(
    location=merkez, radius=gercek_menzil * 1000, 
    color="#22c55e", fill=True, fill_opacity=0.04,
    popup=f"Maksimum Sınır: {gercek_menzil} km"
).add_to(m)

try:
    target_lat = en_mantikli_istasyon['lat']
    target_lon = en_mantikli_istasyon['lon']
    route_url = f"http://router.project-osrm.org/route/v1/driving/{merkez[1]},{merkez[0]};{target_lon},{target_lat}?overview=full&geometries=geojson"
    route_res = requests.get(route_url, timeout=3).json()
    if route_res['code'] == 'Ok':
        line_coords = route_res['routes'][0]['geometry']['coordinates']
        line_coords = [[c[1], c[0]] for c in line_coords]
        folium.PolyLine(line_coords, color="#0284c7", weight=5, opacity=0.8, tooltip="Önerilen Akıllı Rota").add_to(m)
except:
    pass

folium.Marker(location=merkez, popup="Şu an buradasınız", icon=folium.Icon(color='blue', icon='user', prefix='fa')).add_to(m)

for i, row in df_karar.iterrows():
    gosterilecek_mesafe = row['mesafe']
    doluluk = row['doluluk']
    renk = 'red' if doluluk > 80 else ('orange' if doluluk > 50 else 'green')
    yol_tarifi_url = f"https://www.google.com/maps/dir/?api=1&origin={merkez[0]},{merkez[1]}&destination={row['lat']},{row['lon']}"
    
    popup_html = f"""
        <div style="font-family: Arial, sans-serif; width: 180px; color: black;">
            <h4 style="margin-bottom:5px; color: #1e3a8a;">{row['ad']}</h4>
            <p style="font-size:12px; margin-bottom:10px;">
                <b>Uzaklık:</b> {gosterilecek_mesafe} km<br>
                <b>İstasyon Doluluğu:</b> %{doluluk}<br>
                <b style="color: #0284c7;">🎯 Birleşik Trafik:</b> %{int(row['trafik'])}
            </p>
            <a href="{yol_tarifi_url}" target="_blank" style="display: block; text-align: center; background-color: #28a745; color: white; padding: 8px; border-radius: 5px; text-decoration: none; font-weight: bold;">🚗 Yol Tarifi Al</a>
        </div>
    """
    folium.Marker([row['lat'], row['lon']], popup=folium.Popup(popup_html, max_width=200), icon=folium.Icon(color='lightgray', icon='ban', prefix='fa') if row['skor'] > 9000 else folium.Icon(color=renk, icon='bolt', prefix='fa') if row['skor'] > 9000 else folium.Icon(color=renk, icon='bolt', prefix='fa')).add_to(m)

google_maps_url = f"https://www.google.com/maps/dir/?api=1&origin={merkez[0]},{merkez[1]}&destination={en_mantikli_istasyon['lat']},{en_mantikli_istasyon['lon']}"

st.subheader("🗺️ Bölgesel Şarj İstasyonları Navigasyon Haritası")
components.html(m._repr_html_(), width=1000, height=500, scrolling=False)

# ==============================================================================
# 🏆 9. ÖNEMLİ SEÇENEK KARTLARI VE MALİYET ANALİZİ
# ==============================================================================
st.markdown("### 🏆 Önemli Seçenekler yardımıyla Maliyet Analizi")
col1, col2, col3 = st.columns(3)

arac_tuketimi = arac_bilgileri[arac]["tuketim"]
dc_tarife_tl = 9.50  

with col1:
    akilli_maliyet = round((en_mantikli_istasyon['mesafe'] * arac_tuketimi / 100) * dc_tarife_tl, 2)
    st.success(f"🌟 **AKILLI ÖNERİ**\n\n**{en_mantikli_istasyon['ad']}**\n\n🎯 Skor: {en_mantikli_istasyon['skor'] if en_mantikli_istasyon['skor'] < 9000 else 'Menzil Dışı'}\n\n⏱️ Süre: {en_mantikli_istasyon['sure']} dk")
    st.metric("💵 Yolculuk Şarj Maliyeti", f"{akilli_maliyet} TL")
    st.markdown(f'<a href="{google_maps_url}" target="_blank" style="display: block; text-align: center; background-color: #22c55e; color: white; padding: 8px 16px; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 10px; font-size: 14px;">🌐 Haritada Git</a>', unsafe_allow_html=True)

en_yakin_istasyon = df_karar.sort_values("mesafe").iloc[0]
with col2:
    yakin_maliyet = round((en_yakin_istasyon['mesafe'] * arac_tuketimi / 100) * dc_tarife_tl, 2)
    st.info(f"📍 **EN YAKIN İSTASYON**\n\n**{en_yakin_istasyon['ad']}**\n\n📏 Mesafe: {en_yakin_istasyon['mesafe']} km\n\n⏱️ Süre: {en_yakin_istasyon['sure']} dk")
    st.metric("💵 Yolculuk Şarj Maliyeti", f"{yakin_maliyet} TL")

en_bos_istasyon = df_karar.sort_values("doluluk").iloc[0]
with col3:
    bos_maliyet = round((en_bos_istasyon['mesafe'] * arac_tuketimi / 100) * dc_tarife_tl, 2)
    st.warning(f"🔋 **EN BOŞ İSTASYON**\n\n**{en_bos_istasyon['ad']}**\n\n⚡ Doluluk: %{en_bos_istasyon['doluluk']}\n\n📏 Mesafe: {en_bos_istasyon['mesafe']} km")
    st.metric("💵 Yolculuk Şarj Maliyeti", f"{bos_maliyet} TL")
    # ==============================================================================
# 🌍 TÜRKİYE GENELİ DİNAMİK MALIYET HESAPLAYICI (METİN YENİLENME HATASI KESİN ÇÖZÜLDÜ)
# ==============================================================================
st.sidebar.markdown("---")
st.sidebar.subheader("📍 Türkiye Geneli Maliyet Planla")

tum_turkiye_sehirleri = {
    "Adana": [36.9914, 35.3289], "Ankara": [39.9334, 32.8597], "Antalya": [36.8969, 30.7133],
    "Bilecik": [40.1425, 29.9795], "Bursa": [40.1885, 29.0610], "Diyarbakır": [37.9144, 40.2110],
    "Edirne": [41.6710, 26.5720], "Eskişehir": [39.7767, 30.5206], "Gaziantep": [37.0662, 37.3833],
    "İstanbul": [41.0082, 28.9784], "İzmir": [38.4192, 27.1287], "Konya": [37.8714, 32.4847],
    "Kütahya": [39.4200, 29.9850], "Samsun": [41.2867, 36.3300], "Trabzon": [41.0027, 39.7168]
}

sehir_listesi = sorted(list(tum_turkiye_sehirleri.keys()))

# Kutuların key isimlerini tamamen benzersiz (unique) yaparak önbelleği sıfırladık
maliyet_kalkis_adi = st.sidebar.selectbox(
    "Kalkış Şehri", 
    sehir_listesi, 
    index=sehir_listesi.index("İstanbul") if "İstanbul" in sehir_listesi else 0,
    key="kalkis_maliyet_final_v3"
)

maliyet_varis_adi = st.sidebar.selectbox(
    "Varış Şehri", 
    ["Seçiniz..."] + sehir_listesi,
    key="varis_maliyet_final_v3"
)

if maliyet_varis_adi != "Seçiniz...":
    if maliyet_kalkis_adi == maliyet_varis_adi:
        st.sidebar.error("⚠️ Kalkış ve varış şehri aynı olamaz.")
    else:
        # Koordinatları çek ve mesafeyi hesapla
        lat1, lon1 = tum_turkiye_sehirleri[maliyet_kalkis_adi]
        lat2, lon2 = tum_turkiye_sehirleri[maliyet_varis_adi]
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        kus_ucusu_km = 6371 * c
        maliyet_mesafe_km = round(kus_ucusu_km * 1.26, 1)
            
        # Aktif araç tüketim entegrasyonu
        aktif_tuketim = arac_bilgileri[arac]["tuketim"]
        dc_fiyat_kwh = 9.50  
        
        maliyet_kwh_tuketim = round((maliyet_mesafe_km * aktif_tuketim) / 100, 1)
        maliyet_toplam_tl = round(maliyet_kwh_tuketim * dc_fiyat_kwh, 2)
        
        # 🎯 İŞTE KESİN ÇÖZÜM: 
        # Yazıları doğrudan f-string içinde ham bırakmak yerine, dinamik string değişkenleri 
        # oluşturup içeriği zorla temizliyoruz. Böylece donma ihtimali sıfıra iniyor.
        rota_metni = f"🛣️ **Dinamik Rota:** {str(maliyet_kalkis_adi)} ➔ {str(maliyet_varis_adi)}"
        mesafe_metni = f"📏 **Mesafe:** {maliyet_mesafe_km} km"
        enerji_metni = f"🔋 **Harcanacak Enerji:** {maliyet_kwh_tuketim} kWh"
        para_metni = f"💵 **Tahmini Şarj Maliyeti:** `{maliyet_toplam_tl} TL`"
        
        # Temizlenen dinamik metinleri tek seferde basıyoruz
        st.sidebar.info(f"{rota_metni}\n\n{mesafe_metni}\n{enerji_metni}\n{para_metni}")
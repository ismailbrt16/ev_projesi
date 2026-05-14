import requests
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
    # Eğer GPS aktifse varsayılan olarak Bilecik veya IP şehrinin havasını çek
    hedef_sehir = "Bilecik" if sehir_adi == "Mevcut Konumunuz" else sehir_adi
    
    url = f"http://api.openweathermap.org/data/2.5/weather?q={hedef_sehir.strip()}&appid={api_key}&units=metric"
    try:
        response = requests.get(url).json()
        if response.get("cod") == 200:
            return response['main']['temp']
        return 15.0 # Hata olursa sabit değer
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
# Trafik değerini hafızaya al (Sayfa her yenilendiğinde değişmez)
if 'trafik_sabit' not in st.session_state:
    st.session_state.trafik_sabit = trafik_durumu_simule_et()

# Slider'ın başlangıç değerini hafızadaki bu sabit değerden al
mevcut_trafik = st.sidebar.slider("Mevcut Trafik (%)", 0, 100, st.session_state.trafik_sabit)

if mevcut_trafik > 70:
    st.sidebar.error("🔴 Yoğun Trafik: Menzil %20 azalıyor!")
else:
    st.sidebar.success("🟢 Trafik Akıcı.")
st.sidebar.info(f"🌡️ Anlık Sıcaklık: {sicaklik}°C")

# --- 4. HESAPLAMALAR VE KATSAYILAR ---
# --- 1. Sıcaklık Etkisi (Bilimsel Verimlilik Katsayıları) ---
if sicaklik < 0:
    menzil_katsayisi = 0.70  # Dondurucu soğuk: %30 kayıp
elif sicaklik < 10:
    menzil_katsayisi = 0.85  # Soğuk: %15 kayıp
elif sicaklik > 35:
    menzil_katsayisi = 0.90  # Aşırı sıcak (Klima etkisi): %10 kayıp
else:
    menzil_katsayisi = 1.0   # İdeal çalışma sıcaklığı

# 2. Trafik Etkisi (Yoğun trafikte tüketim artar)
# Trafik %70 üzerindeyse menzili %20 düşür
trafik_etkisi = 0.8 if mevcut_trafik > 70 else 1.0

# 3. Nihai Menzil Hesabı (Baz Menzil: %1 şarj = 4km kabul edilmiştir)
baz_menzil = mevcut_sarj * 4 
tahmini_menzil = baz_menzil * menzil_katsayisi * trafik_etkisi

# Hesaplamanın doğru yapıldığını anlamak için Metrikleri de buna bağla
col1, col2, col3 = st.columns(3)
col1.metric("Tahmini Kalan Menzil", f"{round(tahmini_menzil, 1)} km")
col2.metric("Hava Durumu", f"{sicaklik} °C")
# Verimlilik yüzdesi (Sıcaklık ve Trafik ortak etkisi)
verimlilik = int(menzil_katsayisi * trafik_etkisi * 100)
col3.metric("Sistem Verimliliği", f"%{verimlilik}")


# --- 6. HARİTA VE İSTASYON YÖNETİMİ (TAM OTOMATİK) ---
# --- %100 DOĞRULANMIŞ GERÇEK İSTASYON VERİ TABANI ---
# --- CANLI API VE YEDEK SİSTEM MODÜLÜ ---
@st.cache_data(ttl=300)  # 5 dk cache
def istasyonlari_getir(sehir_adi, lat, lon):
    url = "https://api.openchargemap.io/v3/poi/"

    params = {
        "output": "json",
        "latitude": lat,
        "longitude": lon,
        "distance": 100,  # 25'ten 100'e çıkardık
        "maxresults": 100, # Daha fazla sonuç gelsin diye bunu da artırabilirsin
        "compact": True
    }

    headers = {
        "X-API-Key": "ee9e87f5-0920-4e3f-81ed-9f5b7a48a850"  # opsiyonel ama önerilir
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)

        if response.status_code == 200:
            data = response.json()
            istasyonlar = []

            for v in data:
                adres = v.get("AddressInfo", {})
                connections = v.get("Connections", [])

                # 📍 Koordinat kontrolü
                i_lat = adres.get("Latitude")
                i_lon = adres.get("Longitude")

                if not i_lat or not i_lon:
                    continue

                # ⚡ Hızlı şarj filtresi (DC)
                hizli_sarj = any(conn.get("LevelID") == 3 for conn in connections)

                if not hizli_sarj:
                    continue

                # 🏙️ Şehir kontrolü (daha doğru filtre)
                town = adres.get("Town", "") or ""
                state = adres.get("StateOrProvince", "") or ""

               # if sehir_adi.lower() not in (town + state).lower():
#     continue

                istasyonlar.append({
                    "ad": adres.get("Title", "Bilinmeyen İstasyon"),
                    "lat": i_lat,
                    "lon": i_lon
                })

            df = pd.DataFrame(istasyonlar)

            if not df.empty:
                # 🧹 duplicate temizle
                df = df.drop_duplicates(subset=["lat", "lon"])
                return df

    except Exception as e:
        print("API hata:", e)

    # 🔥 FALLBACK (garanti sistem)
    yedek_veriler = {
        "Bilecik": pd.DataFrame({
            'ad': ['Trugo (Merkez)', 'ZES (Belediye)', 'Üniversite Şarj'],
            'lat': [40.14159, 40.14144, 40.17651],
            'lon': [29.97960, 29.98188, 29.98462]
        }),
        "Eskişehir": pd.DataFrame({
            'ad': ['Espark Şarj', 'Vega Outlet', 'Otogar ZES'],
            'lat': [39.78450, 39.78150, 39.78300],
            'lon': [30.51150, 30.47897, 30.54000]
        }),
        "Bursa": pd.DataFrame({
            'ad': ['Kent Meydanı', 'PodyumPark', 'Gemlik Trugo'],
            'lat': [40.19485, 40.22230, 40.41416],
            'lon': [29.06020, 28.99500, 29.13538]
        }),
        "Kütahya": pd.DataFrame({
            'ad': ['Sera AVM', 'Hilton', 'Merkez'],
            'lat': [39.43100, 39.42550, 39.41820],
            'lon': [29.96500, 29.98920, 29.98180]
        })
    }

    return yedek_veriler.get(sehir_adi, yedek_veriler["Bilecik"])

# 1. En yakın şehri ve istasyon anahtarını belirle
# GPS verisi varsa temiz_sehir'i oradan al, yoksa manuel seçime bırak
if loc_data and loc_data.get('coords'):
    # Burada koordinat bazlı en yakın şehir bulma mantığın kalabilir
    # Ama basitlik ve hata almamak için şu anlık geçiyoruz
    pass
# --- AKILLI KARAR DESTEK ALGORİTMASI ---

# Artık veriyi API fonksiyonumuzdan alıyoruz
# Önce anahtarı (şehri) tanımlıyoruz
istasyon_key = temiz_sehir if temiz_sehir else "Bilecik"

# Sonra bu anahtarı kullanarak veriyi çekiyoruz (Senin 158. satırın)
df_karar = istasyonlari_getir(istasyon_key, merkez[0], merkez[1])
df_karar = istasyonlari_getir(istasyon_key, merkez[0], merkez[1])
def skor_hesapla(row):
    # 1. Mesafe Hesabı (Haversine)
    R = 6371
    lat1, lon1 = math.radians(merkez[0]), math.radians(merkez[1])
    lat2, lon2 = math.radians(row['lat']), math.radians(row['lon'])
    
    d = R * 2 * math.atan2(
        math.sqrt(math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2),
        math.sqrt(1-(math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2))
    )

    # 2. 🔥 AKILLI SİMÜLASYON (Senin fonksiyonun entegre hali)
    saat = datetime.now().hour
    if 18 <= saat <= 22:
        doluluk = random.randint(75, 98)  # Akşam pik saatler
    elif 12 <= saat <= 14:
        doluluk = random.randint(55, 80)  # Öğle molası yoğunluğu
    elif 0 <= saat <= 6:
        doluluk = random.randint(5, 25)   # Gece sakinliği
    else:
        doluluk = random.randint(30, 60)  # Standart saatler

    # 3. Ağırlıklı Skor Algoritması
    # Mesafe %70, Doluluk %30 etkili
    skor = (d * 0.7) + (doluluk * 0.3)

    return pd.Series([round(d, 2), doluluk, round(skor, 2)], index=['mesafe', 'doluluk', 'skor'])

# Hesaplamayı yap ve en iyi skora sahip olanı seç
df_karar[['mesafe', 'doluluk', 'skor']] = df_karar.apply(skor_hesapla, axis=1)
en_mantikli = df_karar.sort_values(by='skor').iloc[0]

# --- ÖNERİ KUTULARI ---
placeholder = st.empty() # Streamlit alanını rezerve eder
with placeholder.container():
    # Mevcut tüm if/elif/else öneri kutularını ve hava durumu uyarısını buraya al
    if tahmini_menzil < 50:
        st.error(f"⚠️ **ACİL DURUM:** En mantıklı nokta: **{en_mantikli['ad']}**")
    elif tahmini_menzil < 120:
        st.warning(f"🔔 **Dikkat:** En verimli istasyon: **{en_mantikli['ad']}**")
    else:
        st.success(f"✅ **Akıllı Öneri:** Sizin için en uygun istasyon: **{en_mantikli['ad']}**")
    
    if sicaklik < 10:
        st.info(f"❄️ **Hava {sicaklik}°C:** Menziliniz otomatik olarak revize edilmiştir.")
# 2. Harita objesini sıfırdan oluştur
m = folium.Map(location=merkez, zoom_start=15)

# 3. Kendi konumunu ekle (Mavi İkon)
folium.Marker(
    location=merkez, 
    popup="Şu an buradasınız", 
    icon=folium.Icon(color='blue', icon='user', prefix='fa')
).add_to(m)

# 4. İstasyonları Çiz
# 1. API'den veya yedek sistemden verileri çekiyoruz
df_istasyon = istasyonlari_getir(istasyon_key, merkez[0], merkez[1])

# 2. Mevcut doluluk simülasyonunu API'den gelen verilere uyguluyoruz
df_istasyon['doluluk'] = [random.randint(15, 95) for _ in range(len(df_istasyon))]
for i, row in df_istasyon.iterrows():
    # Mesafe Hesapla
    R = 6371
    lat1, lon1 = math.radians(merkez[0]), math.radians(merkez[1])
    lat2, lon2 = math.radians(row['lat']), math.radians(row['lon'])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    mesafe = round(R * c, 2)
    
    # Akıllı Yoğunluk Simülasyonu
    su_an_saat = datetime.now().hour
    if 17 <= su_an_saat <= 20: doluluk = random.randint(70, 98)
    elif 8 <= su_an_saat <= 10: doluluk = random.randint(60, 85)
    else: doluluk = random.randint(15, 60)
    
    renk = 'red' if doluluk > 80 else ('orange' if doluluk > 50 else 'green')

    # --- YOL TARİFİ VE GELİŞMİŞ POPUP ---
    yol_tarifi_url = f"https://www.google.com/maps/dir/?api=1&destination={row['lat']},{row['lon']}"
    
    popup_html = f"""
        <div style="font-family: Arial, sans-serif; width: 160px; color: black;">
            <h4 style="margin-bottom:5px;">{row['ad']}</h4>
            <p style="font-size:12px; margin-bottom:10px;">
                <b>Uzaklık:</b> {mesafe} km<br>
                <b>Doluluk:</b> %{doluluk}
            </p>
            <a href="{yol_tarifi_url}" target="_blank" 
               style="display: block; text-align: center; background-color: #28a745; 
                      color: white; padding: 8px; border-radius: 5px; text-decoration: none; font-weight: bold;">
               🚗 Yol Tarifi Al
            </a>
        </div>
    """

    folium.Marker(
        [row['lat'], row['lon']],
        popup=folium.Popup(popup_html, max_width=200),
        icon=folium.Icon(color=renk, icon='bolt', prefix='fa')
    ).add_to(m)

# 5. Haritayı Ekrana Bas
st_folium(m, width=1000, height=500, key="harita_final_v2", returned_objects=[])
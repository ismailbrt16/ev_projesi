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

# Sayfa ayarlarını geniş modda başlat (Title'dan önce gelmeli)
st.set_page_config(page_title="EV Karar Destek", layout="wide")

# --- 1. FONKSİYONLAR ---
def istasyon_yogunlugu_hesapla():
    saat = datetime.now().hour
    # İş giriş/çıkış saatlerinde yoğunluk artar
    if (8 <= saat <= 10) or (17 <= saat <= 20):
        return random.randint(60, 95) 
    return random.randint(10, 50)

def konumu_otomatik_bul():
    try:
        g = geocoder.ip('me')
        return g.city if g.city else "Bilecik"
    except:
        return "Bilecik"

def sicaklik_getir(sehir_adi):
    api_key = "5ea92f3cce5b21df053a6fa7f31fd0e5"
    # Şehir ismi koordinat gelirse varsayılan bir değer dön
    if sehir_adi == "Mevcut Konumunuz":
        return 18.5
    url = f"http://api.openweathermap.org/data/2.5/weather?q={sehir_adi.strip()}&appid={api_key}&units=metric"
    try:
        response = requests.get(url).json()
        if response.get("cod") == 200:
            return response['main']['temp']
        return 15.0 
    except:
        return 12.0

def trafik_durumu_simule_et():
    saat = datetime.now().hour
    if (8 <= saat <= 9) or (17 <= saat <= 19):
        return random.randint(70, 95)
    else:
        return random.randint(20, 50)

# --- 2. SAYFA AYARLARI ---
st.set_page_config(page_title="EV Karar Destek", layout="wide")
st.title("⚡ Akıllı Elektrikli Araç Şarj İstasyonu Paneli")

# --- 3. YAN MENÜ (SIDEBAR) & KONUM YÖNETİMİ ---
st.sidebar.header("Araç ve Konum Bilgileri")

# Tarayıcıdan hassas GPS verisi iste
# --- 1. Önce Veritabanını Tanımla (Hata almamak için şart!) ---
sehir_merkezleri = {
    "Bilecik": [40.1425, 29.9795], "Kütahya": [39.4200, 29.9850], "Eskişehir": [39.7767, 30.5206],
    "Bursa": [40.1885, 29.0610], "İstanbul": [41.0082, 28.9784], "Ankara": [39.9334, 32.8597]
}

# --- 63. Satırdan İtibaren Burayı Değiştir ---

# 1. GPS Bileşenini Çağır
loc_data = get_geolocation()

# 2. GPS Verisi Var mı? (Gerçek zamanlı kontrol)
if loc_data and loc_data.get('coords'):
    # GPS verisi geldiği an burası çalışır
    enlem = loc_data['coords']['latitude']
    boylam = loc_data['coords']['longitude']
    merkez = [enlem, boylam]
    
    # Sunumda kanıtlamak için koordinatı yazdırıyoruz
    st.sidebar.success(f"✅ GPS Bağlandı: {round(enlem,4)}, {round(boylam,4)}")
    
    # Haritayı bu konuma kilitlemek için session_state kullanıyoruz
    st.session_state.user_location = loc_data
    temiz_sehir = "Bilecik" # İstasyonları çekmek için varsayılan şehir
else:
    # 3. GPS Yoksa veya İzin Bekleniyorsa
    otomatik_sehir = konumu_otomatik_bul()
    sehir_input = st.sidebar.text_input("Şehir Bilgisi", otomatik_sehir)
    temiz_sehir = sehir_input.strip().title()
    # sehir_merkezleri sözlüğünden koordinat çek
    merkez = sehir_merkezleri.get(temiz_sehir, [40.1425, 29.9795])
    
    if loc_data is None:
        st.sidebar.warning("📡 GPS aranıyor / İzin bekleniyor...")
    else:
        st.sidebar.info("🌐 IP tabanlı konum kullanılıyor.")

# --- 86. Satır: Sıcaklık (Aynı Kalıyor) ---
sicaklik = sicaklik_getir(temiz_sehir)

# --- 86. Satır: Sıcaklık (Aynı Kalıyor) ---
sicaklik = sicaklik_getir(temiz_sehir)

# --- 76. Satır ve Sonrası (Sıcaklık ve Diğerleri) ---
sicaklik = sicaklik_getir(temiz_sehir)

# --- 77. Satır: Sıcaklık Getir (Aynı Kalıyor) ---
sicaklik = sicaklik_getir(temiz_sehir)

sicaklik = sicaklik_getir(temiz_sehir)
arac = st.sidebar.selectbox("Aracınız", ["Togg T10X", "Tesla Model Y", "Fiat 500e"])
mevcut_sarj = st.sidebar.slider("Mevcut Şarj (%)", 0, 100, 40)
otomatik_trafik = trafik_durumu_simule_et()
mevcut_trafik = st.sidebar.slider("Mevcut Trafik (%)", 0, 100, otomatik_trafik)

# Trafik Durum Mesajı
if mevcut_trafik > 70:
    st.sidebar.error("🔴 Yoğun Trafik: Menzil %20 azalıyor!")
else:
    st.sidebar.success("🟢 Trafik Akıcı.")

st.sidebar.info(f"🌡️ Anlık Sıcaklık: {sicaklik}°C")

# --- 4. HESAPLAMALAR ---
menzil_katsayisi = 0.8 if sicaklik < 5 else 1.0
trafik_etkisi = 0.8 if mevcut_trafik > 70 else 1.0
tahmini_menzil = (mevcut_sarj * 4) * menzil_katsayisi * trafik_etkisi

# --- 5. METRİKLER ---
col1, col2, col3 = st.columns(3)
col1.metric("Tahmini Kalan Menzil", f"{round(tahmini_menzil, 1)} km")
col2.metric("Hava Durumu", f"{sicaklik} °C")
col3.metric("Sistem Verimliliği", f"%{int(menzil_katsayisi * 100)}")

# --- 6. AKILLI ÖNERİ MEKANİZMASI ---
st.markdown("---")

# GPS açıksa "Mevcut Konumunuz" yazar, bu durumda öneriyi Bilecik'e göre yaparız
# GPS kapalıysa kullanıcının yazdığı şehri (temiz_sehir) kullanırız
oneri_sehri = "Bilecik" if temiz_sehir == "Mevcut Konumunuz" else temiz_sehir

istasyon_onerileri = {
    "Bilecik": "Trugo (Hükümet Meydanı)",
    "Kütahya": "ZES (Lalin Garden)",
    "Eskişehir": "Eşarj (Espark AVM)",
    "Bursa": "Trugo (Togg Gemlik Tesisi)",
    "Ankara": "Eşarj (Armada AVM)",
    "İstanbul": "ZES (Zorlu Center)"
}

onerilen_istasyon = istasyon_onerileri.get(oneri_sehri, "En yakın yüksek hızlı DC istasyonu")

# ÖNERİ KUTUSU (Geri gelen kısım burası)
if tahmini_menzil < 50:
    st.error(f"⚠️ **Menzil Kritik!** Kalan: {round(tahmini_menzil, 1)} km.")
    st.info(f"💡 **Öneri:** {oneri_sehri} sınırlarındaki **{onerilen_istasyon}** noktasına gidin.")
elif tahmini_menzil < 120:
    st.warning(f"🔔 **Dikkat:** Menzil azalıyor. **{onerilen_istasyon}** üzerinden geçmeniz rasyonel olur.")
else:
    st.success(f"✅ **Yolculuk Güvenli:** Mevcut menzil yeterli. Şarj gerekirse **{onerilen_istasyon}** en iyi seçenektir.")

st.markdown("---")

# --- 1. VERİLERİ TANIMLA (En Başta Olmalı) ---
istasyon_verileri = {
    "Bilecik": pd.DataFrame({'ad': ['Trugo', 'Eşarj', 'ZES'], 'lat': [40.142, 40.145, 40.150], 'lon': [29.979, 29.975, 29.985]}),
    "Bursa": pd.DataFrame({'ad': ['Trugo (Gemlik)', 'ZES (Podyum)'], 'lat': [40.428, 40.222], 'lon': [29.155, 28.995]}),
    "Kütahya": pd.DataFrame({'ad': ['ZES (Lalin)', 'Eşarj (Vazo)'], 'lat': [39.421, 39.418], 'lon': [29.986, 29.982]}),
    "Eskişehir": pd.DataFrame({'ad': ['Eşarj (Espark)', 'ZES'], 'lat': [39.776, 39.780], 'lon': [30.520, 30.530]})
}

st.subheader(f"📍 {temiz_sehir} Yakınındaki Şarj İstasyonları")

# 2. HARİTA OBJESİNİ OLUŞTUR (Titremeyi engelleyen session_state kontrolü)
if 'map_obj' not in st.session_state:
    st.session_state.map_obj = folium.Map(location=merkez, zoom_start=14)

m = st.session_state.map_obj

# Konum değişirse haritayı oraya odakla
if loc_data:
    m.location = merkez

# 3. Mavi İkon (Senin Konumun)
folium.Marker(
    location=merkez, 
    popup="Şu an buradasınız", 
    icon=folium.Icon(color='blue', icon='user', prefix='fa')
).add_to(m)

# 4. İSTASYONLARI ÇİZ
istasyon_key = "Bilecik" if temiz_sehir == "Mevcut Konumunuz" else temiz_sehir
df_istasyon = istasyon_verileri.get(istasyon_key, pd.DataFrame(columns=['ad', 'lat', 'lon']))

for i, row in df_istasyon.iterrows():
    # Mesafe Hesapla
    R = 6371
    lat1, lon1 = math.radians(merkez[0]), math.radians(merkez[1])
    lat2, lon2 = math.radians(row['lat']), math.radians(row['lon'])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    mesafe = round(R * c, 2)
    
    # Yoğunluk ve Renk (random import edilmiş olmalı)
    doluluk = random.randint(10, 95)
    renk = 'red' if doluluk > 80 else ('orange' if doluluk > 50 else 'green')

    folium.Marker(
        [row['lat'], row['lon']],
        popup=f"<b>{row['ad']}</b><br>Uzaklık: {mesafe} km<br>Doluluk: %{doluluk}",
        icon=folium.Icon(color=renk, icon='bolt', prefix='fa')
    ).add_to(m)

# 5. HARİTAYI EKRANA BAS (Sürekli yenilemeyi durduran satırlar)
st_folium(
    m, 
    width=1000, 
    height=500, 
    key="harita_final", 
    returned_objects=[] # Bu boş liste titremeyi durdurur
)
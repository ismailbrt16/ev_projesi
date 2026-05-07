import streamlit as st
import geocoder
# ... diğer importlar ...
import random 
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import requests
from datetime import datetime
import geocoder 

def konumu_otomatik_bul():
    try:
        g = geocoder.ip('me')
        return g.city if g.city else "Bilecik"
    except:
        return "Bilecik"
    
def sicaklik_getir():
    api_key = "5ea92f3cce5b21df053a6fa7f31fd0e5"
    
    # İşte 2. kısım buraya geliyor:
    otomatik_sehir = konumu_otomatik_bul()
    sehir = st.sidebar.text_input("Şehir Bilgisi", otomatik_sehir)
    
    url = f"http://api.openweathermap.org/data/2.5/weather?q={sehir}&appid={api_key}&units=metric"
    
    try:
        response = requests.get(url).json()
        if response.get("cod") != 200:
            return 20
        return response['main']['temp']
    except:
        return 20

 # Bağlantı hatası olursa varsayılan değer

def trafik_durumu_simule_et():
    saat = datetime.now().hour
    if (8 <= saat <= 9) or (17 <= saat <= 19):
        return random.randint(70, 95) 
    elif (0 <= saat <= 6):
        return random.randint(5, 15)
    else:
        return random.randint(30, 50)
    

# Sayfa Ayarları
st.set_page_config(page_title="EV Karar Destek", layout="wide")

st.title("⚡ Akıllı Elektrikli Araç Şarj İstasyonu Paneli")

# 1. Yan Menü (Sidebar) - Girişler
st.sidebar.header("Araç ve Konum Bilgileri")
arac = st.sidebar.selectbox("Aracınız", ["Togg T10X", "Tesla Model Y", "Fiat 500e"])
mevcut_sarj = st.sidebar.slider("Mevcut Şarj (%)", 0, 100, 40)
# Trafik durumunu simüle eden fonksiyonu çağırıyoruz
otomatik_trafik = trafik_durumu_simule_et()
# Trafik sürgüsünü ekliyoruz
mevcut_trafik = st.sidebar.slider("Mevcut Trafik (%)", 0, 100, otomatik_trafik)

# Gerçek sıcaklığı API'den çekiyoruz
sicaklik = sicaklik_getir() 

# Kullanıcıya Bilecik'in anlık havasını bildirelim
st.sidebar.info(f"📍 Bilecik Anlık Sıcaklık: {sicaklik}°C")

# 2. Mantık (Logic) - Menzil Hesaplama (Basit bir formül)
# 2. Mantık (Logic) - Menzil Hesaplama
menzil_katsayisi = 0.8 if sicaklik < 5 else 1.0

# --- YENİ EKLEME: Trafik Etkisi ---
trafik_etkisi = 1.0
if mevcut_trafik > 70:
    trafik_etkisi = 0.85 # Yoğun trafikte %15 kayıp
elif mevcut_trafik > 40:
    trafik_etkisi = 0.95 # Orta trafikte %5 kayıp

# Menzil hesabını trafik etkisiyle çarpıyoruz
tahmini_menzil = (mevcut_sarj * 4) * menzil_katsayisi * trafik_etkisi
# --- AKILLI ÖNERİ MEKANİZMASI ---
st.markdown("---") 
if tahmini_menzil < 50:
    st.error(f"⚠️ **Menzil Kritik!** Kalan menziliniz {tahmini_menzil:.1f} km.")
    st.info("💡 **Sizin için en yakın ve mantıklı şarj noktası:** Bilecik Merkez'deki **Trugo Şarj İstasyonu (Hükümet Meydanı)**.")
elif tahmini_menzil < 100:
    st.warning(f"🔔 **Dikkat:** Menziliniz {tahmini_menzil:.1f} km. **Trugo (OSB Girişi)** üzerinden geçmeniz mantıklı olabilir.")
else:
    st.success(f"✅ **Yolculuk Güvenli:** Menziliniz yeterli. Şarj ihtiyacı duyarsanız en mantıklı seçenek **Eşarj (Merkez)** istasyonudur.")
st.markdown("---")

# 3. Ana Panel - Metrikler
col1, col2, col3 = st.columns(3)
col1.metric("Tahmini Kalan Menzil", f"{tahmini_menzil} km")
col2.metric("Anlık Hava Durumu", f"{sicaklik} °C")
col3.metric("Sistem Verimliliği", f"%{int(menzil_katsayisi * 100)}")

# 4. Harita Verisi (Örnek İstasyonlar)
# Kaç tane istasyonun varsa o kadar rastgele durum üretir
# Listende 4 istasyon olduğu için range(4) kullanıyoruz
durumlar = [random.choice(['Boş', 'Dolu']) for _ in range(4)]

data = pd.DataFrame({
    'ad': ['Zes enerji istasyonu', 'trugo Şarj İstasyonu', 'WAT Mobilite Şarj İstasyonu', 'E- Şarj Şarj İstasyonu'],
    'lat': [40.09552, 40.14605, 40.16971, 40.27192],
    'lon': [30.01417, 29.98185, 29.97899, 29.69947],
    'doluluk': durumlar # Burası artık her seferinde değişecek
})

st.subheader("📍 Yakınımdaki Şarj İstasyonları")
m = folium.Map(location=[40.1467, 29.9745], zoom_start=13)

for i, row in data.iterrows():
    color = "green" if row['doluluk'] == "Boş" else "red"
    folium.Marker(
        [row['lat'], row['lon']], 
        popup=f"{row['ad']} - {row['doluluk']}",
        icon=folium.Icon(color=color)
    ).add_to(m)

st_folium(m, width=700, height=450)
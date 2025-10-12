from fastapi import Request

UI_STRINGS = {
  'id': {
    'nav_about': 'Tentang Kami', 'nav_portfolio': 'Portofolio', 'nav_info': 'Info', 'nav_contact': 'Kontak',
    'nav_news': 'Berita', 'nav_press': 'Siara Pers', 'nav_procurement': 'Informasi Pengadaan', 'nav_gallery': 'Galeri',
    'lang_id': 'ID', 'lang_en': 'EN', 'lang_ar': 'AR', 'read_more': 'Selengkapnya', 'send': 'Kirim'
  },
  'en': {
    'nav_about': 'About Us', 'nav_portfolio': 'Our Portfolio', 'nav_info': 'Info', 'nav_contact': 'Contact',
    'nav_news': 'News', 'nav_press': 'Press Release', 'nav_procurement': 'Procurement Info', 'nav_gallery': 'Gallery',
    'lang_id': 'ID', 'lang_en': 'EN', 'lang_ar': 'AR', 'read_more': 'Read more', 'send': 'Send'
  },
  'ar': {
    'nav_about': 'من نحن', 'nav_portfolio': 'أعمالنا', 'nav_info': 'معلومات', 'nav_contact': 'اتصل بنا',
    'nav_news': 'الأخبار', 'nav_press': 'البيانات الصحفية', 'nav_procurement': 'معلومات المشتريات', 'nav_gallery': 'المعرض',
    'lang_id': 'إند', 'lang_en': 'إنج', 'lang_ar': 'عر', 'read_more': 'اقرأ المزيد', 'send': 'إرسال'
  }
}
DEFAULT_LANG = 'id'

async def resolve_lang(request: Request) -> str:
    q = request.query_params.get('lang')
    if q in UI_STRINGS:
        return q
    cookie = request.cookies.get('lang')
    if cookie in UI_STRINGS:
        return cookie
    return DEFAULT_LANG

class I18n:
    def __init__(self, lang: str):
        self.lang = lang
    def t(self, key: str) -> str:
        return UI_STRINGS.get(self.lang, UI_STRINGS[DEFAULT_LANG]).get(key, key)

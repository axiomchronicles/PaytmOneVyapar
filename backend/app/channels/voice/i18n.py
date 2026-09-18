"""Internationalization and localized voice responses for Vyapaar Voice Agent.

All agent responses use polite, natural female assistant phrasing.

Supports major Indian languages:
- Hindi (hi-IN) - Female assistant (कर रही हूँ, जोड़ सकी)
- Gujarati (gu-IN) - Female assistant (કરી રહી છું, જોડી શકી નથી)
- Bengali (bn-IN) - Female assistant (তৈরি করছি)
- Bhojpuri (bho-IN) - Female assistant (बनावत बानी, समझ नइखीं पा रहल)
- Tamil (ta-IN) - Female assistant (தயாரிக்கிறேன், செயல்படுத்த முடியவில்லை)
- Telugu (te-IN) - Female assistant (చేస్తున్నాను, ప్రాసెస్ చేయలేకపోయాను)
- Marathi (mr-IN) - Female assistant (तयार करत आहे, करू शकले नाही)
- English (en-IN / default fallback)
"""

VOICE_MESSAGES: dict[str, dict[str, str]] = {
    "hi-IN": {
        "low_stock": "कम इन्वेंट्री दर्ज की गई। मैं मांग के पूर्वानुमान की जांच कर रही हूँ।",
        "purchase_request": "खरीद अनुरोध दर्ज कर लिया गया है। कृपया अनुमोदन से पहले प्रस्ताव की समीक्षा करें।",
        "proposal_approved": "खरीद प्रस्ताव स्वीकृत हो गया है। सप्लायर को आर्डर भेज दिया गया है।",
        "proposal_modified": "खरीद प्रस्ताव संशोधित कर दिया गया है।",
        "proposal_rejected": "खरीद प्रस्ताव अस्वीकार कर दिया गया है।",
        "no_active_proposal": "इस वॉइस सत्र से कोई सक्रिय खरीद प्रस्ताव लिंक नहीं है।",
        "unknown_action": "मैं इस अनुरोध को किसी सुरक्षित व्यावसायिक कार्य से नहीं जोड़ सकी।",
    },
    "gu-IN": {
        "low_stock": "ઓછો સ્ટોક નોંધાયો છે. હું માંગના પૂર્વાનુમાનની તપાસ કરી રહી છું.",
        "purchase_request": "ખરીદીની વિનંતી સમજાઈ ગઈ છે. કૃપા કરીને મંજૂરી પહેલાં દરખાસ્તની સમીક્ષા કરો.",
        "proposal_approved": "ખરીદી દરખાસ્ત મંજૂર કરવામાં આવી છે. સપ્લાયરને ઓર્ડર મોકલી દીધો છે.",
        "proposal_modified": "ખરીદી દરખાસ્તમાં ફેરફાર કરવામાં આવ્યો છે.",
        "proposal_rejected": "ખરીદી દરખાસ્ત રદ કરવામાં આવી છે.",
        "no_active_proposal": "આ વૉઇસ સત્ર સાથે કોઈ સક્રિય ખરીદ દરખાસ્ત જોડાયેલી નથી.",
        "unknown_action": "હું આ વિનંતીને યોગ્ય વ્યવસાયિક ક્રિયા સાથે જોડી શકી નથી.",
    },
    "bn-IN": {
        "low_stock": "কম স্টক লক্ষ্য করা গেছে। আমি চাহিদার পূর্বাভাস দেখে ক্রয়ের প্রস্তাব তৈরি করছি।",
        "purchase_request": "ক্রয় অনুরোধ পেয়েছি। অনুমোদনের আগে তৈরি প্রস্তাবটি পর্যালোচনা করুন।",
        "proposal_approved": "ক্রয় প্রস্তাব অনুমোদিত হয়েছে। সাপ্লায়ারকে অর্ডার পাঠিয়ে দেওয়া হয়েছে।",
        "proposal_modified": "ক্রয় প্রস্তাব সংশোধন করা হয়েছে।",
        "proposal_rejected": "ক্রয় প্রস্তাব বাতিল করা হয়েছে।",
        "no_active_proposal": "এই ভয়েস সেশনের সাথে কোনো সক্রিয় ক্রয় প্রস্তাব যুক্ত নেই।",
        "unknown_action": "আমি এই অনুরোধটি কোনো নিরাপদ ব্যবসায়িক প্রক্রিয়ার সাথে মেলাতে পারছি না।",
    },
    "bho-IN": {
        "low_stock": "कम माल दर्ज हो गइल बा। हम डिमांड देख के खरीद के प्रस्ताव बनावत बानी।",
        "purchase_request": "खरीद के निहोरा दर्ज हो गइल बा। मंजूरी से पहिले परस्ताव देख लीं।",
        "proposal_approved": "खरीद प्रस्ताव पास हो गइल। सप्लायर के आर्डर भेज दिहल गइल बा।",
        "proposal_modified": "खरीद प्रस्ताव बदल दिहल गइल बा।",
        "proposal_rejected": "खरीद प्रस्ताव रद्द कs दिहल गइल बा।",
        "no_active_proposal": "एह आवाज सत्र से कवनो चालू खरीद प्रस्ताव नइखे जुड़ल।",
        "unknown_action": "हम ई बात समझ नइखीं पा रहल।",
    },
    "ta-IN": {
        "low_stock": "குறைந்த இருப்பு பதிவு செய்யப்பட்டது. தேவை முன்னறிவிப்பை சரிபார்த்து கொள்முதல் திட்டம் தயாரிக்கிறேன்.",
        "purchase_request": "கொள்முதல் கோரிக்கை ஏற்றுக்கொள்ளப்பட்டது. ஒப்புதலுக்கு முன் முன்மொழிவை மதிப்பாய்வு செய்யவும்.",
        "proposal_approved": "கொள்முதல் ஒப்புதல் அளிக்கப்பட்டது. சப்ளையருக்கு ஆர்டர் அனுப்பப்பட்டுள்ளது.",
        "proposal_modified": "கொள்முதல் மாற்றம் செய்யப்பட்டுள்ளது.",
        "proposal_rejected": "கொள்முதல் நிராகரிக்கப்பட்டது.",
        "no_active_proposal": "இந்த குரல் அமர்வில் செயலில் உள்ள கொள்முதல் முன்மொழிவு எதுவும் இணைக்கப்படவில்லை.",
        "unknown_action": "இந்த கோரிக்கையை என்னால் செயல்படுத்த முடியவில்லை.",
    },
    "te-IN": {
        "low_stock": "తక్కువ నిల్వ నమోదైంది. డిమాండ్ అంచనా వేసి కొనుగోలు ప్రతిపాదన సిద్ధం చేస్తున్నాను.",
        "purchase_request": "కొనుగోలు అభ్యర్థన అందింది. ఆమోదించే ముందు రూపొందించిన ప్రతిపాదనను సమీక్షించండి.",
        "proposal_approved": "కొనుగోలు ప్రతిపాదన ఆమోదించబడింది. సరఫరాదారుకు ఆర్డర్ పంపబడింది.",
        "proposal_modified": "కొనుగోలు ప్రతిపాదన సవరించబడింది.",
        "proposal_rejected": "కొనుగోలు ప్రతిపాదన తిరస్కరించబడింది.",
        "no_active_proposal": "ఈ వాయిస్ సెషన్‌కు యాక్టివ్ కొనుగోలు ప్రతిపాదన ఏదీ లింక్ చేయబడలేదు.",
        "unknown_action": "ఈ అభ్యర్థనను నేను ప్రాసెస్ చేయలేకపోయాను.",
    },
    "mr-IN": {
        "low_stock": "कमी स्टॉक नोंदवला गेला आहे. मी मागणीचा अंदाज घेऊन खरेदी प्रस्ताव तयार करत आहे.",
        "purchase_request": "खरेदीची विनंती समजली आहे. मंजुरीपूर्वी तयार केलेल्या प्रस्तावाची पडताळणी करा.",
        "proposal_approved": "खरेदी प्रस्ताव मंजूर झाला आहे. सप्लायरला ऑर्डर पाठवली आहे.",
        "proposal_modified": "खरेदी प्रस्तावात बदल करण्यात आला आहे.",
        "proposal_rejected": "खरेदी प्रस्ताव नाकारला गेला आहे.",
        "no_active_proposal": "या व्हॉइस सत्राशी कोणताही सक्रिय खरेदी प्रस्ताव जोडलेला नाही.",
        "unknown_action": "मी या विनंतीला सुरक्षित व्यावसायिक कृतीमध्ये रूपांतरित करू शकले नाही.",
    },
    "en-IN": {
        "low_stock": "Low inventory noted. I am checking the demand forecast before proposing a purchase.",
        "purchase_request": "I understood the purchase request. Please review the generated proposal before approval.",
        "proposal_approved": "Purchase proposal approved. Order executed with supplier.",
        "proposal_modified": "Purchase proposal modified.",
        "proposal_rejected": "Purchase proposal rejected.",
        "no_active_proposal": "No authenticated active purchase proposal is linked to this voice session.",
        "unknown_action": "I could not map that request to a safe business action.",
    },
}


def get_voice_message(key: str, language_code: str | None = None) -> str:
    """Retrieve localized message for a key given a BCP-47 language code."""
    lang = language_code or "en-IN"
    if lang in VOICE_MESSAGES:
        selected_lang = lang
    elif lang.startswith("hi"):
        selected_lang = "hi-IN"
    elif lang.startswith("gu"):
        selected_lang = "gu-IN"
    elif lang.startswith("bn"):
        selected_lang = "bn-IN"
    elif lang.startswith("bho"):
        selected_lang = "bho-IN"
    elif lang.startswith("ta"):
        selected_lang = "ta-IN"
    elif lang.startswith("te"):
        selected_lang = "te-IN"
    elif lang.startswith("mr"):
        selected_lang = "mr-IN"
    else:
        selected_lang = "en-IN"

    messages = VOICE_MESSAGES.get(selected_lang, VOICE_MESSAGES["en-IN"])
    return messages.get(key, VOICE_MESSAGES["en-IN"].get(key, ""))

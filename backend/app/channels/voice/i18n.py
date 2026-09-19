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
        "greeting": "नमस्ते! मैं बढ़िया हूँ। आपकी दुकान में आज मैं क्या मदद कर सकती हूँ? स्टॉक देखना हो या कोई नया आर्डर लगाना हो तो बताएं।",
        "capabilities": "मैं आपकी एआई मुनीम हूँ। मैं दुकान का स्टॉक ट्रैक कर सकती हूँ, कम इन्वेंट्री पर अलर्ट दे सकती हूँ, और सप्लायर आर्डर मैनेज करने में मदद करती हूँ।",
        "general_help": "जी, मैं आपकी बात समझ रही हूँ। आप मुझसे दुकान के स्टॉक, सप्लायर्स, आर्डर या व्यापार से जुड़े किसी भी सवाल के बारे में पूछ सकते हैं।",
        "inventory_all_good": "आपकी दुकान की सभी इन्वेंट्री ठीक है। कोई भी आइटम कम स्टॉक में नहीं है।",
        "no_pending_proposals": "अभी कोई भी खरीद प्रस्ताव पेंडिंग नहीं है।",
        "low_stock": "कम इन्वेंट्री दर्ज की गई। मैं मांग के पूर्वानुमान की जांच कर रही हूँ।",
        "purchase_request": "खरीद अनुरोध दर्ज कर लिया गया है। कृपया अनुमोदन से पहले प्रस्ताव की समीक्षा करें।",
        "proposal_approved": "खरीद प्रस्ताव स्वीकृत हो गया है। सप्लायर को आर्डर भेज दिया गया है।",
        "proposal_modified": "खरीद प्रस्ताव संशोधित कर दिया गया है।",
        "proposal_rejected": "खरीद प्रस्ताव अस्वीकार कर दिया गया है।",
        "no_active_proposal": "इस समय कोई सक्रिय खरीद प्रस्ताव पेंडिंग नहीं है। क्या आप कम स्टॉक की जांच करना चाहते हैं?",
        "unknown_action": "मैं आपकी बात समझ रही हूँ। बताइए दुकान के स्टॉक या आर्डर में मैं क्या सहायता करूँ?",
    },
    "gu-IN": {
        "greeting": "નમસ્તે! હું મજામાં છું. તમારી દુકાનમાં આજે હું શું મદદ કરી શકું? સ્ટોક જોવો હોય કે નવો ઓર્ડર આપવો હોય તો કહો.",
        "capabilities": "હું તમારી AI મુનીમ છું. હું દુકાનનો સ્ટોક ટ્રેક કરી શકું છું અને સપ્લાયર ઓર્ડર મેનેજ કરવામાં મદદ કરું છું.",
        "general_help": "હા, હું તમારી વાત સમજી રહી છું. તમે મને દુકાનના સ્ટોક, સપ્લાયર્સ અથવા વેપાર સંબંધિત કોઈ પણ પ્રશ્ન પૂછી શકો છો.",
        "inventory_all_good": "તમારી દુકાનમાં તમામ સ્ટોક પૂરતો છે. કોઈ વસ્તુ ઓછી નથી.",
        "no_pending_proposals": "હમણાં કોઈ ખરીદ દરખાસ્ત બાકી નથી.",
        "low_stock": "ઓછો સ્ટોક નોંધાયો છે. હું માંગના પૂર્વાનુમાનની તપાસ કરી રહી છું.",
        "purchase_request": "ખરીદીની વિનંતી સમજાઈ ગઈ છે. કૃપા કરીને મંજૂરી પહેલાં દરખાસ્તની સમીક્ષા કરો.",
        "proposal_approved": "ખરીદી દરખાસ્ત મંજૂર કરવામાં આવી છે. સપ્લાયરને ઓર્ડર મોકલી દીધો છે.",
        "proposal_modified": "ખરીદી દરખાસ્તમાં ફેરફાર કરવામાં આવ્યો છે.",
        "proposal_rejected": "ખરીદી દરખાસ્ત રદ કરવામાં આવી છે.",
        "no_active_proposal": "આ વૉઇસ સત્ર સાથે કોઈ સક્રિય ખરીદ દરખાસ્ત જોડાયેલી નથી. શું તમે ઓછો સ્ટોક તપાસવા માંગો છો?",
        "unknown_action": "હું તમારી વાત સમજી રહી છું. કહો દુકાનના સ્ટોક કે ઓર્ડરમાં હું શું મદદ કરું?",
    },
    "bn-IN": {
        "greeting": "নমস্কার! আমি ভালো আছি। আপনার দোকানের কাজে আজ কীভাবে সাহায্য করতে পারি? স্টক দেখতে চান নাকি নতুন অর্ডার দিতে চান?",
        "capabilities": "আমি আপনার এআই মুনিম। আমি দোকানের স্টক ট্র্যাক করতে পারি এবং সাপ্লায়ার অর্ডার ম্যানেজ করতে সাহায্য করি।",
        "general_help": "হ্যাঁ, আমি বুঝতে পারছি। আপনি আমাকে দোকানের স্টক, সাপ্লায়ার বা ব্যবসা সংক্রান্ত যেকোনো প্রশ্ন করতে পারেন।",
        "inventory_all_good": "আপনার দোকানের সব স্টক পর্যাপ্ত আছে। কোনো পণ্য কম নেই।",
        "no_pending_proposals": "বর্তমানে কোনো কেনাকাটার প্রস্তাব অনুমোদনের অপেক্ষায় নেই।",
        "low_stock": "কম স্টক লক্ষ্য করা গেছে। আমি চাহিদার পূর্বাভাস দেখে ক্রয়ের প্রস্তাব তৈরি করছি।",
        "purchase_request": "ক্রয় অনুরোধ পেয়েছি। অনুমোদনের আগে তৈরি প্রস্তাবটি পর্যালোচনা করুন।",
        "proposal_approved": "ক্রয় প্রস্তাব অনুমোদিত হয়েছে। সাপ্লায়ারকে অর্ডার পাঠিয়ে দেওয়া হয়েছে।",
        "proposal_modified": "ক্রয় প্রস্তাব সংশোধন করা হয়েছে।",
        "proposal_rejected": "ক্রয় প্রস্তাব বাতিল করা হয়েছে।",
        "no_active_proposal": "এই ভয়েস সেশনের সাথে কোনো সক্রিয় ক্রয় প্রস্তাব যুক্ত নেই। আপনি কি কম স্টক পরীক্ষা করতে চান?",
        "unknown_action": "আমি আপনার কথা বুঝতে পারছি। বলুন দোকানের স্টক বা অর্ডার সংক্রান্ত কী সাহায্য করতে পারি?",
    },
    "bho-IN": {
        "greeting": "प्रणाम! हम एकदम ठीक बानी। आज रउआ दुकान में का मदद करीं? स्टॉक देखे के बा कि नया आर्डर लगावे के बा, बताईं।",
        "capabilities": "हम रउआ एআই मुनीम बानी। हम दोकान के माल चेक कर सकेनी आ सप्लायर आर्डर संभाले में मदद करेनी।",
        "general_help": "हँ, हम बात समझत बानी। रउआ दोकान के माल, सप्लायर चाहे ब्यापार से जुड़ल कवनो सवाल पूछ सकेनी।",
        "inventory_all_good": "रउआ दोकान के कुल माल ठीक बा। कवनो सामान कम नइखे।",
        "no_pending_proposals": "अभी कवनो खरीद परस्ताव बाकी नइखे।",
        "low_stock": "कम माल दर्ज हो गइल बा। हम डिमांड देख के खरीद के प्रस्ताव बनावत बानी।",
        "purchase_request": "खरीद के निहोरा दर्ज हो गइल बा। मंजूरी से पहिले परस्ताव देख लीं।",
        "proposal_approved": "खरीद प्रस्ताव पास हो गइल। सप्लायर के आर्डर भेज दिहल गइल बा।",
        "proposal_modified": "खरीद प्रस्ताव बदल दिहल गइल बा।",
        "proposal_rejected": "खरीद प्रस्ताव रद्द कs दिहल गइल बा।",
        "no_active_proposal": "एह आवाज सत्र से कवनो चालू खरीद प्रस्ताव नइखे जुड़ल। का रउआ कम माल के जांच करल चाहत बानी?",
        "unknown_action": "हम रउआ बात समझत बानी। बताईं दोकान के माल चाहे आर्डर में का मदद करीं?",
    },
    "ta-IN": {
        "greeting": "வணக்கம்! நான் நலமாக இருக்கிறேன். உங்கள் கடைக்கு இன்று நான் என்ன உதவி செய்ய வேண்டும்? இருப்பு சரிபார்க்கவா அல்லது புதிய ஆர்டர் செய்யவா?",
        "capabilities": "நான் உங்கள் AI முனிம். நான் கடையின் இருப்பை கண்காணிக்கவும் சப்ளையர் ஆர்டர்களை நிர்வகிக்கவும் உதவுகிறேன்.",
        "general_help": "ஆம், நான் புரிந்துகொள்கிறேன். கடையின் இருப்பு, சப்ளையர்கள் அல்லது வணிகம் பற்றி நீங்கள் என்னிடம் கேட்கலாம்.",
        "inventory_all_good": "உங்கள் கடையின் இருப்பு போதுமானதாக உள்ளது. எந்தப் பொருளும் குறைவாக இல்லை.",
        "no_pending_proposals": "தற்போது நிலுவையில் உள்ள கொள்முதல் திட்டங்கள் எதுவும் இல்லை.",
        "low_stock": "குறைந்த இருப்பு பதிவு செய்யப்பட்டது. தேவை முன்னறிவிப்பை சரிபார்த்து கொள்முதல் திட்டம் தயாரிக்கிறேன்.",
        "purchase_request": "கொள்முதல் கோரிக்கை ஏற்றுக்கொள்ளப்பட்டது. ஒப்புதலுக்கு முன் முன்மொழிவை மதிப்பாய்வு செய்யவும்.",
        "proposal_approved": "கொள்முதல் ஒப்புதல் அளிக்கப்பட்டது. சப்ளையருக்கு ஆர்டர் அனுப்பப்பட்டுள்ளது.",
        "proposal_modified": "கொள்முதல் மாற்றம் செய்யப்பட்டுள்ளது.",
        "proposal_rejected": "கொள்முதல் நிராகரிக்கப்பட்டது.",
        "no_active_proposal": "இந்த குரல் அமர்வில் செயலில் உள்ள கொள்முதல் முன்மொழிவு எதுவும் இணைக்கப்படவில்லை.",
        "unknown_action": "நான் புரிந்துகொள்கிறேன். உங்கள் கடையின் இருப்பு அல்லது ஆர்டரில் நான் எவ்வாறு உதவ முடியும்?",
    },
    "te-IN": {
        "greeting": "నమస్కారం! నేను బాగున్నాను. ఈరోజు మీ దుకాణంలో నేను ఏ విధంగా సహాయపడగలను? స్టాక్ తనిఖీ చేయాలా లేదా కొత్త ఆర్డర్ ఇవ్వాలా?",
        "capabilities": "నేను మీ AI మునిమ్. నేను దుకాణం స్టాక్ ట్రాక్ చేసి, సప్లయర్ ఆర్డర్లను నిర్వహించడంలో సహాయపడతాను.",
        "general_help": "అవును, నేను అర్థం చేసుకుంటున్నాను. దుకాణం స్టాక్, సరఫరాదారులు లేదా వ్యాపారం గురించి మీరు నన్ను అడగవచ్చు.",
        "inventory_all_good": "మీ దుకాణంలో మొత్తం స్టాక్ సరిపడా ఉంది. ఏ వస్తువు తక్కువగా లేదు.",
        "no_pending_proposals": "ప్రస్తుతం ఏ కొనుగోలు ప్రతిపాదనలు పెండింగ్‌లో లేవు.",
        "low_stock": "తక్కువ నిల్వ నమోదైంది. డిమాండ్ అంచనా వేసి కొనుగోలు ప్రతిపాదన సిద్ధం చేస్తున్నాను.",
        "purchase_request": "కొనుగోలు అభ్యర్థన అందింది. ఆమోదించే ముందు రూపొందించిన ప్రతిపాదనను సమీక్షించండి.",
        "proposal_approved": "కొనుగోలు ప్రతిపాదన ఆమోదించబడింది. సరఫరాదారుకు ఆర్డర్ పంపబడింది.",
        "proposal_modified": "కొనుగోలు ప్రతిపాదన సవరించబడింది.",
        "proposal_rejected": "కొనుగోలు ప్రతిపాదన తిరస్కరించబడింది.",
        "no_active_proposal": "ఈ వాయిస్ సెషన్‌కు యాక్టివ్ కొనుగోలు ప్రతిపాదన ఏదీ లింక్ చేయబడలేదు.",
        "unknown_action": "నేను అర్థం చేసుకుంటున్నాను. మీ దుకాణం స్టాక్ లేదా ఆర్డర్‌లలో నేను ఎలా సహాయపడగలను?",
    },
    "mr-IN": {
        "greeting": "नमस्कार! मी मजेत आहे. आज तुमच्या दुकानात मी काय मदत करू शकते? स्टॉक तपासायचा आहे की नवीन ऑर्डर द्यायची आहे?",
        "capabilities": "मी तुमची AI मुनीम आहे. मी दुकानातील स्टॉक ट्रॅक करू शकते आणि सप्लायर ऑर्डर व्यवस्थापित करण्यात मदत करते.",
        "general_help": "होय, मला समजले. तुम्ही मला दुकानातील स्टॉक, सप्लायर्स किंवा व्यवसायाबद्दल काहीही विचारू शकता.",
        "inventory_all_good": "तुमच्या दुकानातील सर्व स्टॉक पुरेशा प्रमाणात आहे. कोणतीही वस्तू कमी नाही.",
        "no_pending_proposals": "सध्या कोणताही खरेदी प्रस्ताव प्रलंबित नाही.",
        "low_stock": "कमी स्टॉक नोंदवला गेला आहे. मी मागणीचा अंदाज घेऊन खरेदी प्रस्ताव तयार करत आहे.",
        "purchase_request": "खरेदीची विनंती समजली आहे. मंजुरीपूर्वी तयार केलेल्या प्रस्तावाची पडताळणी करा.",
        "proposal_approved": "खरेदी प्रस्ताव मंजूर झाला आहे. सप्लायरला ऑर्डर पाठवली आहे.",
        "proposal_modified": "खरेदी प्रस्तावात बदल करण्यात आला आहे.",
        "proposal_rejected": "खरेदी प्रस्ताव नाकारला गेला आहे.",
        "no_active_proposal": "या व्हॉइस सत्राशी कोणताही सक्रिय खरेदी प्रस्ताव जोडलेला नाही. आपल्याला कमी स्टॉक तपासायचा आहे का?",
        "unknown_action": "मला समजले. दुकानातील स्टॉक किंवा ऑर्डरबद्दल मी काय मदत करू शकते?",
    },
    "en-IN": {
        "greeting": "Hello! I am doing well. How can I help with your store today? You can ask about stock, orders, or suppliers.",
        "capabilities": "I am your AI Munim. I track store inventory, alert you on low stock, and help negotiate and approve supplier orders.",
        "general_help": "I understand. Feel free to ask about your store inventory, pending orders, suppliers, or general business questions.",
        "inventory_all_good": "All your inventory levels are healthy. No items are currently low on stock.",
        "no_pending_proposals": "There are no purchase proposals pending approval right now.",
        "low_stock": "Low inventory noted. I am checking the demand forecast before proposing a purchase.",
        "purchase_request": "I understood the purchase request. Please review the generated proposal before approval.",
        "proposal_approved": "Purchase proposal approved. Order executed with supplier.",
        "proposal_modified": "Purchase proposal modified.",
        "proposal_rejected": "Purchase proposal rejected.",
        "no_active_proposal": "There is no active purchase proposal linked to this voice session. Would you like to check low stock or start a new order?",
        "unknown_action": "I am listening. How can I help with your shop stock, orders, or business today?",
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

"""
filter.py - URL filter + contact cleaner + post-crawl validator
Patch v2: thêm foreign TLD reject, email CN/fake, VN phone check, dedup email.
"""

import re
from urllib.parse import urlparse

# ══════════════════════════════════════════════════════════════════════
#  L1A: DOMAIN BLACKLIST
# ══════════════════════════════════════════════════════════════════════
BLACKLIST = {
    "merriam-webster.com","dictionary.com","cambridge.org","wikipedia.org",
    "britannica.com","vocabulary.com","vietjack.com","hoc247.net",
    "loigiaihay.com","toanmath.com","violet.vn","tailieu.vn",
    "luatminhkhue.vn","thegioiluat.vn","luatvietnam.vn","investopedia.com",
    "wikihow.com","accountingcoach.com","accountingverse.com",
    "thefreedictionary.com","iciba.com","eudic.net","financestrategists.com",
    "vnexpress.net","tuoitre.vn","thanhnien.vn","dantri.com.vn",
    "vietnamnet.vn","baomoi.com","zing.vn","kenh14.vn",
    "vietcetera.com","kr-asia.com","e27.co","technode.global",
    "techcrunch.com","forbes.com","bloomberg.com","reuters.com",
    "wired.com","theverge.com","techcollectivesea.com",
    "thegradient.pub","the-shiv.com","apacbusinessheadlines.com",
    "cxodigitalpulse.com","bestdevops.com","creationsforu.com",
    "justsomecrypto.com","edtechagency.net","techsciblog.com",
    "vicsguide.com","hkbav.org","conventuslaw.com","limericktime.com",
    "bizasean.com","saigonist.com","pcmag.com","techradar.com","zdnet.com",
    "bbc.com","bbc.co.uk","theinfostride.com","note8.vn","techtimes.vn",
    "techz.vn","vnito.org","u2u.xyz","dealstreetasia.com","asiapevc.com",
    "privateequityinternational.com","businessnewsasia.com",
    "asianprivatebanker.com","internationalbanker.com","techwireasia.com",
    "jumpstartmag.com","livebitcoinnews.com","bitcoinnewsasia.com",
    "vietnamfinance.vn","vietnamstar.net","robots.net","startuprise.org",
    "hivelife.com","iglu.net","finovate.com","theactuarymagazine.org",
    "asianbankingandfinance.net","thefintechmag.com","vuihoc.vn",
    "finshare.vn","kinhtevadubao.vn","swinburne-vn.edu.vn",
    "hocvientaichinh.com.vn","eventseye.com","findawealthmanager.com",
    "edisongroup.com","cri-report.com","vhs80.com","blogstoread.com",
    "findarticleonline.com","nationsencyclopedia.com","vietreader.com",
    "mylangroup.com","jaycorriveau.com",
    "statista.com","mordorintelligence.com","techsciresearch.com",
    "blueweaveconsulting.com","expertmarketresearch.com",
    "marketresearchvietnam.com","researchinvietnam.com",
    "itif.org","viettonkinconsulting.com","growyourbusiness.org",
    "clutch.co","goodfirms.co","techbehemoths.com","sortlist.com",
    "designrush.com","upcity.com","manifest.com","tracxn.com",
    "crunchbase.com","zoominfo.com","appdevelopmentcompanies.co",
    "topsoftwarecompanies.co","beststartup.asia","failory.com",
    "superbcompanies.com","incorp.asia","listicle.sgpgrid.com",
    "consultancy.org","softwarecompanynetwork.com","globalsoftwarecompanies.com",
    "topon.tech","ensun.io","bestarion.com","techcrawlr.com",
    "vietnamyello.com","investasian.com","pitchbook.com","aurigininc.com",
    "alphasearch.com","dataforthai.com","topmybusiness.com",
    "companyincorporationvietnam.com","soopage.com",
    "linkedin.com","itviec.com","vietnamworks.com","topcv.vn",
    "jobstreet.com","wellfound.com","thesaasjobs.com","vieclam24h.vn",
    "careerlink.vn","freelancer.com","upwork.com","ufind.name",
    "gov.vn","chinhphu.vn","mps.gov.vn","bocongan.gov.vn",
    "trade.gov","worldbank.org","adb.org","oecd.org","rpta.wp.gov.lk",
    "eib.org","finca.org","incometax.gov.in","mta.gov.mn","cpta.mn",
    "taxacc.mn","legalinfo.mn","legalinstitute.mn","gov.uk","hkma.gov.hk",
    "scb.co.th","scbeic.com","fundsupermart.in.th","finnomena.com",
    "settrade.com","fmgfunds.com","alquity.com","airafactoring.co.th",
    "cmdf.or.th","philippine.co.th","labuanibfc.com","goforex.eu",
    "ceylinco-insurance.com","srilankainsurance.com",
    "shopify.com","salesforce.com","blockchain.com","deepai.org",
    "chatgpt.com","openai.com","microsoft.com","google.com","amazon.com",
    "apple.com","ibm.com","oracle.com","gameloft.com","atlassian.com",
    "hubspot.com","geeksforgeeks.org","w3schools.com","stackoverflow.com",
    "stackexchange.com","reddit.com","quora.com","mckinsey.com",
    "ey.com","kpmg.com","deloitte.com","pwc.com","lendingpoint.com",
    "transfez.com","instarem.com","xoom.com","fxcompared.com",
    "thinkwithgoogle.com","hubbis.com","henleyglobal.com",
    "poki.com","y8.com","pacogames.com","playhop.com","miniclip.com",
    "addictinggames.com","crazygames.com","playgama.com","bgames.com",
    "hahagames.com","kizi.com","friv.com","agame.com","silvergames.com",
    "gameflare.com","gamesgo.net","gamepix.com","yahoo.com",
    "cellphones.com.vn","thegioididong.com","fptshop.com.vn",
    "hanoimobile.vn","chungmobile.com","bachhoaxanh.com","tiki.vn",
    "shopee.vn","lazada.vn","sendo.vn","mobilecity.vn","minhtuanmobile.com",
    "2tmobile.com","hoanghamobile.com","hoanghamobile.vn","onewaymobile.vn",
    "hungmobile.vn","nguyenkim.com","dienmayxanh.com","mediamart.vn",
    "pico.vn","topzone.vn","concung.com","vpbank.com.vn",
    "sj.qq.com","baidu.com","zhihu.com","taobao.com","qq.com","weibo.com",
    "money18.on.cc",
    "sitestat.com","siteindices.com","usitestat.com","prsync.com",
    "pr-inside.com","52wmb.com","usaypage.com","buyer.usaypage.com",
    "medium.com","substack.com","blogspot.com","wordpress.com",
    "pbworks.com","soha.vn","tratu.soha.vn","tradebrio.com",
    "hikingproject.com","bocasay.com","10times.com","eventbrite.com",
    "web.de","intowindows.com","techstation.vn","consulting.com",
    "vnm.soopage.com","jcsearch.com","saigonbao.com","norbr.com",
    "visionfund.org","ukadslist.com","live4cup.com","longislandjobsmagazine.com",
    "getjobber.com","expat.com","qlipso.com",
    "coinotag.com",
    # [PATCH] Thêm các site nước ngoài phổ biến bị lọt
    "runoob.com","w3school.com","tutorialspoint.com","javatpoint.com",
    "kahoot.com","kahoot.it","buyabans.com","othoba.com",
    "daraz.pk","flipkart.com","snapdeal.com","meesho.com",
    "lonelyplanet.com","tripadvisor.com","booking.com","agoda.com",
    "adventuresofjellie.com","marketresearch.com",
    # [PATCH V3] Thêm Báo chí, Job Board, SaaS nước ngoài
    "congan.com.vn","suckhoedoisong.vn","baochinhphu.vn","vtv.vn","cand.com.vn",
    "hoteljob.vn","timviec365.vn","careerbuilder.vn","glints.com",
    "smallpdf.com","moovit.com",
    # [PATCH V4] Thêm domains rác từ phân tích top 100
    "sider.ai", "agencyvn.com", "vietnix.vn", "tuyensinh.uel.edu.vn",
    "jobthai.com", "mobileworld.com.vn", "softvn.vn", "blacksnetwork.net",
    "bachlongmobile.com", "vietpedia.vn",
}

# ══════════════════════════════════════════════════════════════════════
#  [PATCH] FOREIGN TLD BLACKLIST — reject domain nước ngoài rõ ràng
# ══════════════════════════════════════════════════════════════════════
FOREIGN_TLDS = {
    ".th",      # Thái Lan
    ".bd",      # Bangladesh
    ".cn",      # Trung Quốc
    ".fi",      # Phần Lan
    ".lk",      # Sri Lanka
    ".pk",      # Pakistan
    ".in",      # Ấn Độ (trừ .com.vn)
    ".au",      # Úc
    ".uk",      # Anh (co.uk cũng bị bắt)
    ".de",      # Đức
    ".fr",      # Pháp
    ".jp",      # Nhật (site JP, không phải .com.vn/jp)
    ".kr",      # Hàn
    ".my",      # Malaysia
    ".id",      # Indonesia
    ".ph",      # Philippines
}

# ══════════════════════════════════════════════════════════════════════
#  L1B: PATH BLACKLIST
# ══════════════════════════════════════════════════════════════════════
BAD_PATHS = [
    "/blog/","/news/","/article/","/articles/","/dictionary/","/wiki/",
    "/guide/","/guides/","/what-is/","/how-to/","/definition/",
    "/insights/","/insight/","/report/","/research/","/publication/",
    "/publications/","/post/","/posts/","/press/","/industry-reports/",
    "/market-intelligence/","/resources/","/learn/","/tutorial/",
    "/hoi-dap/","/thu-thuat/","/kien-thuc/","/tin-tuc/","/bai-viet/",
    "/ly-thuyet/","/cach-tinh-","/companies/","/agencies/","/developers/",
    "/explore/","/d/explore/","/directory/","/location/","/startups/",
    "/freelancers/","/jobs/","/hire/","/user/","/profile/","/author/",
    "/tag/","/category/","/topic/","/outlook/","/statistics/","/forecast/",
    "/terms/","/forum/","/community/","/discussion/","/buyer/","/dict/",
    "/vat-ly-","/toan-","/knowledge_hub/","/archive-daily/",
    "/send-money","/send-money-to","/personal-loan","/personal-tax",
    "/mutual","/fund/filter","/fund/","/manager-comment",
    "/intl/en-","/en/products/loans/","/th/detail/",
    "/fintech-la-gi","/blockchain-la-gi","/startup-la-gi",
    "/thpt-hieu-ro-","/cong-va-cong-suat",
]

# ══════════════════════════════════════════════════════════════════════
#  L1C: SLUG BLACKLIST
# ══════════════════════════════════════════════════════════════════════
BAD_SLUGS = [
    "top-10","top-20","top-5","top-15","best-","companies-in","companies-list",
    "list-of","ranking-","danh-sach","xu-huong","what-is-","how-to-",
    "guide-to-","overview-of-","market-size","market-report","industry-report",
    "forecast-","statistics-","in-depth","raises-","-funding-","series-a",
    "series-b","a-sneak-peek","deep-dive","cach-go-","cach-viet-","cach-tinh-",
    "huong-dan-","ly-thuyet-","monthly-report","annual-report","encyclopedia",
    "dictionary","msockid=","how-does-lend","how-vietnam","developing-vietnam",
    "venture-capital-lat","vietnam-spearheading","roshi-enters-v",
    "5-companies-comp","lenddoefl-launches","transfer-money",
    "send-money","payment-methods","venture-capitals","wealth-management-forum",
    "fintech-la-gi","blockchain-la-gi","startup-la-gi","lend",
]

# ══════════════════════════════════════════════════════════════════════
#  L2: POST-CRAWL DESCRIPTION VALIDATOR
# ══════════════════════════════════════════════════════════════════════
REJECT_DESC_PHRASES = [
    "latest news","breaking news","tin tức mới","báo điện tử",
    "read our blog","tin công nghệ","read more articles",
    "the meaning of","definition of","learn what","how to use in a sentence",
    "lesson","lý thuyết","bài tập","học sinh","học viên",
    "market size","market share","cagr","compound annual growth",
    "market forecast","key players include","segmented by","table of contents",
    "buy report","download report","request sample",
    "find companies","browse companies","list of companies",
    "top companies in","best companies in","compare companies",
    "danh sách công ty",
    "bitcoin block explorer","crypto transaction search",
    "blockchain explorer","nft marketplace",
    "road passenger authority","western province passengers",
    "online games","play free","browser games","html5 games",
    "press release newswire","media outreach",
    "scholarship","tuition","admissions",
    "mutual fund","fund performance","nav history","stock exchange",
    "personal loan calculator","loan eligibility",
    # [PATCH V3] Thêm từ khóa tin tức báo chí
    "tin tức","báo điện tử","toà soạn","tổng biên tập","chuyên trang tin tức","giấy phép mạng xã hội",
]

ACCEPT_DESC_PHRASES = [
    "we are a","our company","our team of","our clients",
    "chúng tôi là","công ty chúng tôi","dịch vụ của chúng tôi",
    "years of experience","founded in","established in","since 20",
    "we provide","we offer","our services include","contact us today",
    "request a quote","book a demo","get in touch",
    "liên hệ với chúng tôi","nhận báo giá",
]

def validate_description(description: str) -> tuple:
    if not description:
        return True, ""
    low = description.lower()
    for phrase in REJECT_DESC_PHRASES:
        if phrase in low:
            return False, f"desc_reject:{phrase[:30]}"
    return True, ""


# ══════════════════════════════════════════════════════════════════════
#  L1 FILTER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════
def _get_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().replace("www.", "")
    except:
        return ""

def _get_path(url: str) -> str:
    try:
        return urlparse(url).path.lower()
    except:
        return ""

def _get_slug(url: str) -> str:
    try:
        p = urlparse(url)
        return (p.path + ("?" + p.query if p.query else "")).lower()
    except:
        return url.lower()

def _is_article_pattern(url: str) -> bool:
    slug = _get_slug(url)
    if re.search(r"/20\d{2}/\d{2}/\d{2}/", slug):
        return True
    segments = [s for s in _get_path(url).split("/") if s]
    if len(segments) >= 2:
        last = segments[-1]
        if len(last) > 70 and last.count("-") > 6:
            return True
    return False

# [PATCH] Check foreign TLD — ưu tiên .vn, reject rõ ràng nước ngoài
def _is_foreign_tld(domain: str) -> bool:
    # Cho phép domain có chứa .vn (ưu tiên tuyệt đối)
    if domain.endswith(".vn") or ".vn." in domain:
        return False
    # Reject các TLD nước ngoài rõ ràng
    for tld in FOREIGN_TLDS:
        if domain.endswith(tld):
            return True
    return False

def filter_url(url: str) -> tuple:
    """Returns (keep, reason)."""
    if not url or not url.startswith("http"):
        return False, "invalid"

    domain = _get_domain(url)
    path   = _get_path(url)
    slug   = _get_slug(url)

    # Domain blacklist
    if domain in BLACKLIST:
        return False, f"blacklist:{domain}"
    for bd in BLACKLIST:
        if domain.endswith("." + bd):
            return False, f"blacklist_sub:{bd}"

    # [PATCH] Foreign TLD check
    if _is_foreign_tld(domain):
        return False, f"foreign_tld:{domain}"

    # TLD filter (gov, edu)
    if any(domain.endswith(t) for t in [".edu",".gov",".gov.lk",".gov.mn",".or.th"]):
        return False, "bad_tld"

    # Path blacklist
    for bp in BAD_PATHS:
        if bp in path:
            return False, f"bad_path:{bp}"

    # Slug blacklist
    for kw in BAD_SLUGS:
        if kw in slug:
            return False, f"bad_slug:{kw}"

    # Article URL pattern
    if _is_article_pattern(url):
        return False, "article_pattern"

    # SEO artifacts
    if any(x in url for x in ["siteindices.com","usitestat.com"]):
        return False, "seo_artifact"

    return True, ""

def filter_urls(urls: list) -> tuple:
    kept, stats = [], {}
    for url in urls:
        keep, reason = filter_url(url)
        if keep:
            kept.append(url)
        else:
            cat = reason.split(":")[0]
            stats[cat] = stats.get(cat, 0) + 1
    return kept, stats


# ══════════════════════════════════════════════════════════════════════
#  L3: EMAIL + PHONE CLEANER
# ══════════════════════════════════════════════════════════════════════
BAD_EMAIL_RE = [
    r"sentry",r"wixpress",r"bug-report",r"bug-reporting",
    r"^name@",r"^your@",r"^youname@",r"^enteryour@",
    r"@email\.com$",r"@yourcompany\.com$",r"@addresshere\.",
    r"@example\.com$",r"^test@",r"^demo@",r"^u003e",
    r"photo-shared-by",r"tagging-@",r"@company\.com$",r"@mail\.com$",
    r"^[a-f0-9]{20,}@",r"u002f@",r"@avif$",r"@2x\.",
    r"@robots\.net$",r"@benzingaheadlines",r"@sharecomms",
    r"^nckh\.",r"^efilingwebmanager",r"@incometax",
    r"^--",
    r"@tradepassglobal",r"@asiapevc",r"@eventsnewsasia",
    r"@dealstreetasia",r"@businessnewsasia",
    # [PATCH V3] Bad email prefixes
    r"^toasoan@",r"^ads@",r"^dev@",r"^chimaivir@",r"^bvmtw@",
    # [PATCH] Email Trung Quốc / số / fake phổ biến
    r"@sohu\.com$",
    r"@qq\.com$",
    r"@163\.com$",
    r"@126\.com$",
    r"@sina\.com$",
    r"^\d{5,}@",           # email toàn số (kiểu sohu bot)
    r"^user@",
    r"^example@",
    r"@myorg\.com$",
    r"_@",                 # prefix kiểu _@domain (lonelyplanet trap)
    r"^[a-f0-9\-]{30,}@", # hash dài (tracking pixel email)
]

BAD_EMAIL_DOMAINS = {
    "sentry.io","wixpress.com","sentry-next.wixpress.com",
    "example.com","yourcompany.com","addresshere.com",
    "websitere.net","bug-reporting-xalgha6.m-w.com",
    "robots.net","benzingaheadlines.com","sharecomms.co.uk",
    "tradepassglobal.com","peimedia.com","pei.group",
    "asiapevc.com","eventsnewsasia.com","dealstreetasia.com",
    "businessnewsasia.com","soa.org","insider.llc",
    "lhdfirm.com",
    # [PATCH]
    "sohu.com","qq.com","163.com","126.com","sina.com","sina.cn",
    "myorg.com","schema.org","w3.org","cloudflare.com",
    "textilestudycenter.com",  # Bangladesh
    "electronics.org",         # fake org domain
}

# [PATCH] TLD email nước ngoài rõ ràng — reject email domain
FOREIGN_EMAIL_TLDS = {".fi",".bd",".lk",".pk",".th",".cn"}

def is_valid_email(email: str) -> bool:
    if not email or "@" not in email or len(email) > 100:
        return False
    low = email.lower()
    domain = low.split("@")[-1]
    prefix = low.split("@")[0]

    if domain in BAD_EMAIL_DOMAINS:
        return False

    # [PATCH] Reject email domain nước ngoài rõ ràng
    for ftld in FOREIGN_EMAIL_TLDS:
        if domain.endswith(ftld):
            return False

    for pat in BAD_EMAIL_RE:
        if re.search(pat, low):
            return False

    if len(prefix) > 50:
        return False
    return True

def clean_emails(emails) -> list:
    if isinstance(emails, str):
        emails = [e.strip() for e in emails.split(",") if e.strip()]
    return [e for e in emails if is_valid_email(e)]

def email_matches_website(email: str, website: str) -> bool:
    """
    Kiểm tra xem email domain có khớp với website domain không.
    Bỏ qua nếu email là personal (gmail, yahoo...).
    """
    if not email or "@" not in email or not website:
        return True
        
    email_domain = email.split("@")[-1].lower()
    try:
        from urllib.parse import urlparse
        site_domain = urlparse(website).netloc.lower().replace("www.", "")
    except:
        return True
        
    personal_domains = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com"}
    if email_domain in personal_domains:
        return True
        
    # Match nếu domain này chứa domain kia
    return email_domain in site_domain or site_domain in email_domain

def is_valid_vn_phone(phone: str) -> bool:
    cleaned = re.sub(r"[^\d+]", "", phone)
    if cleaned.startswith("+84"):
        cleaned = "0" + cleaned[3:]
    elif cleaned.startswith("84") and len(cleaned) == 11:
        cleaned = "0" + cleaned[2:]
    return bool(re.fullmatch(r"0[35789]\d{8}", cleaned))

def clean_phones(phones) -> list:
    if isinstance(phones, str):
        phones = [p.strip() for p in phones.split(",") if p.strip()]
    return [p for p in phones if is_valid_vn_phone(p)]


# ══════════════════════════════════════════════════════════════════════
#  [PATCH] VN LEAD VALIDATOR — dùng trong crawl_one() của tool.py
# ══════════════════════════════════════════════════════════════════════
VN_PHONE_PREFIXES = ("03","05","07","08","09","+84","84")

def is_vietnam_lead(url: str, phones_str: str = "") -> bool:
    """
    Trả về True nếu lead khả năng cao là công ty Việt Nam.
    Ưu tiên: domain .vn → True ngay.
    Fallback: có số điện thoại VN hợp lệ.
    Không có cả 2 → False (reject).
    """
    domain = _get_domain(url)
    # Ưu tiên tuyệt đối: .vn domain
    if domain.endswith(".vn"):
        return True
    # Fallback: phone VN
    if phones_str:
        cleaned = re.sub(r"[\s\-\.\(\)]", "", phones_str)
        if any(cleaned.startswith(p) for p in VN_PHONE_PREFIXES):
            return True
    return False


# ══════════════════════════════════════════════════════════════════════
#  [PATCH] DEDUP HELPER — dùng trong apply_filter() của tool.py
# ══════════════════════════════════════════════════════════════════════
def dedup_leads(leads: list) -> tuple:
    """
    Nhận list dict leads đã pass filter.
    Trả về (passed, duplicates) — mỗi email/domain chỉ giữ 1 lead tốt nhất.
    """
    seen_emails  = set()
    seen_domains = set()
    passed, dupes = [], []

    def _root_domain(url):
        try:
            parts = url.split("//")[-1].split("/")[0].split(".")
            return ".".join(parts[-2:]) if len(parts) >= 2 else url
        except:
            return url

    for lead in leads:
        em  = str(lead.get("best_email","")).strip().lower()
        dom = _root_domain(str(lead.get("website","")))

        is_dup = False
        if em and em not in ("", "nan"):
            if em in seen_emails:
                is_dup = True
            else:
                seen_emails.add(em)

        if not is_dup and dom:
            if dom in seen_domains:
                is_dup = True
            else:
                seen_domains.add(dom)

        if is_dup:
            dupes.append({**lead, "reject_reason": "duplicate"})
        else:
            passed.append(lead)

    return passed, dupes
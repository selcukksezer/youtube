"""Topic-bound procedural fallback narrations by niche family."""


def _topic_bound_narrations(subject: str, is_tr: bool, family: str = "", nid: str = "") -> list:
    """One subject, ten distinct beats. Natural human storytelling progression without mechanical repetitions."""
    if nid == "12_amazon_affiliate":
        if is_tr:
            return [
                "Gündelik hayatınızı inanılmaz derecede kolaylaştıracak ve gördüğünüzde hemen denemek isteyeceğiniz 3 harika ürün var.",
                "İlk ürün, evinizde veya mutfağınızda açık kalan paketleri hava almaz şekilde saniyeler içinde kapatan şarjlı mini poşet mühürleyici.",
                "Yiyeceklerin bayatlamasını ve dökülmesini tamamen önleyerek mutfakta inanılmaz bir pratiklik sağlıyor.",
                "İkinci ürün, masa ve tezgah üzerindeki tüm kablo ve küçük eşya karmaşasını tek hamlede toparlayan manyetik akıllı düzenleyici.",
                "Kompakt tasarımı sayesinde hem yerden tasarruf ettiriyor hem de dağınık görüntüyü anında ortadan kaldırıyor.",
                "Üçüncü ürün ise ergonomik yapısıyla temizlik ve bakım işlerini yarı yarıya hafifleten çok fonksiyonlu temizleme cihazı.",
                "Ulaşılması en zor dar köşelerdeki kir ve tozları zahmetsizce temizleyerek harcanan enerjiyi sıfıra indiriyor.",
                "Bu pratik çözümler sayesinde gün içinde zaman ve enerjinizi çok daha verimli kullanabilirsiniz.",
                "Küçük gibi görünen bu akıllı araçlar, alışkanlıklarınızı ve yaşam konforunuzu baştan sona değiştiriyor.",
                "Peki bu üç yenilikçi üründen sizce hangisi evinizde en çok işe yarardı? Yorumlarda buluşalım.",
            ]
        return [
            "Here are three viral gadgets that solve everyday problems and instantly upgrade your daily life.",
            "The first item is a portable handheld heat sealer that locks opened snack bags airtight in seconds.",
            "It completely prevents food from going stale and keeps your pantry neatly organized with zero effort.",
            "The second gadget is a magnetic smart cable organizer that clears clutter off your desk instantly.",
            "Its sleek compact profile saves precious workspace while keeping all your charging cables within reach.",
            "The third tool is a versatile multi-function cleaning device engineered for tight, hard-to-reach corners.",
            "It eliminates dust and grime effortlessly without scratching delicate gadgets or home surfaces.",
            "These three practical solutions save you hours of frustration throughout your busy routine.",
            "Small innovations like these make a massive difference in your daily living comfort and focus.",
            "Which of these three viral finds would you use most around your home? Let us know below.",
        ]

    if family == "tech" or nid == "21_ai_tools_hacks":
        if is_tr:
            return [
                f"{subject} alanında işinizi ve üretkenliğinizi katlayacak devrim niteliğinde yapay zeka araçları var.",
                "İlk araç, saatler süren karmaşık araştırmaları ve veri analizini saniyeler içinde kaynaklı olarak önünüze getiriyor.",
                "İkinci araç, tek bir komutla profesyonel sunumlar, arayüzler ve içerikler üreterek iş akışınızı baştan sona hızlandırıyor.",
                "Üçüncü platform ise yaratıcı üretimi ve otomasyonu stüdyo kalitesinde zahmetsizce yönetmenizi sağlıyor.",
                "Bu akıllı çözümler sayesinde geleneksel ve yorucu çalışma alışkanlıkları tamamen geride kalıyor.",
                "Peki siz günlük işlerinizde en çok hangi yapay zeka aracını kullanıyorsunuz? Yorumlarda paylaşın.",
            ]
        return [
            f"Here are groundbreaking AI tools that will completely supercharge your workflow in {subject}.",
            "The first tool automates hours of tedious research and synthesizes verified facts in seconds.",
            "The second platform generates professional presentations, code, and content from a single prompt.",
            "The third tool delivers studio-quality creative assets and intelligent automation effortlessly.",
            "Integrating these smart tools completely transforms how much you can achieve each day.",
            "Which of these AI tools are you most excited to try? Let us know in the comments.",
        ]

    if family == "automotive" or nid == "31_supercars_automotive":
        if is_tr:
            return [
                f"{subject} dünyasında sınırları zorlayan ve nefes kesen inanılmaz mühendislik harikaları var.",
                "İlk canavar, 0'dan 100'e 2 saniyenin altında çıkarak yer çekimine adeta meydan okuyor.",
                "İkinci model, aerodinamik gövdesi ve çift turbo motoruyla yarış pistlerini titretiyor.",
                "Üçüncü hiper araba ise milyon dolarlık fiyat etiketi ve benzersiz karbonfiber tasarımıyla zirvede yer alıyor.",
                "Bu olağanüstü makineler, saf gücün ve ileri otomotiv teknolojisinin en uç noktasını temsil ediyor.",
                "Peki bu 3 süper arabadan hangisini garajınızda görmek isterdiniz? Yorumlarda buluşalım.",
            ]
        return [
            f"Here are breathtaking engineering masterpieces pushing absolute limits in {subject}.",
            "The first beast shatters expectations by launching from 0 to 60 in under 2 seconds.",
            "The second machine dominates the track with twin-turbo performance and active aerodynamics.",
            "The third hypercar stands at the pinnacle with multi-million dollar exclusivity and carbon fiber mastery.",
            "These mechanical beasts represent the extreme frontier of speed, design, and raw power.",
            "Which of these dream supercars would you park in your garage? Let us know in the comments.",
        ]

    if family == "fitness" or nid == "23_fitness_nutrition_hacks":
        if is_tr:
            return [
                f"{subject} konusunda vücudunuzu dönüştürecek ve yağ yakımını hızlandıracak bilimsel tüyolar var.",
                "İlk kural, antrenman öncesi doğru beslenerek enerji depolarını maksimum seviyeye çıkarmaktır.",
                "İkinci prensip, kas hipertrofisini tetikleyen progressive overload tekniğini doğru formla uygulamaktır.",
                "Üçüncü adım ise kaliteli uyku ve toparlanma süreciyle kas onarımını en üst seviyeye taşımaktır.",
                "Bu basit ama etkili kuralları disiplinle uyguladığınızda sonuçları çok daha kısa sürede görebilirsiniz.",
                "Peki siz antrenmanlarınızda bu kurallardan hangisini aksatıyorsunuz? Yorumlarda tartışalım.",
            ]
        return [
            f"Here are science-backed training and nutrition hacks to transform your physique in {subject}.",
            "The first rule is optimizing your pre-workout nutrition to fuel maximum power and fat oxidation.",
            "The second principle is progressive overload executed with strict form to stimulate continuous growth.",
            "The third key is prioritizing deep sleep and active recovery for peak muscle synthesis.",
            "Consistently applying these fundamentals produces dramatic physical changes in record time.",
            "Which of these fitness habits do you struggle with most? Let us know in the comments.",
        ]

    if family == "legal" or nid == "32_legal_consumer_hacks":
        if is_tr:
            return [
                f"{subject} alanında her vatandaşın ve tüketicinin mutlaka bilmesi gereken hayati haklar var.",
                "İlk hak, haksız veya ayıplı ürünlerde sorgusuz sualsiz değişim veya tam para iadesi hakkınızdır.",
                "İkinci kural, sözleşmelerde gizlenen haksız şartların kanunen tamamen geçersiz sayılmasıdır.",
                "Üçüncü önemli nokta ise yasal süreler içinde resmi itiraz hakkınızı kullanarak mağduriyeti önlemektir.",
                "Bu temel kuralları bildiğinizde hiçbir mağaza veya kurum sizi mağdur edemez.",
                "Peki bu tüketici haklarından herhangi birini daha önce kullandınız mı? Yorumlarda paylaşın.",
            ]
        return [
            f"Here are critical consumer and everyday legal rights everyone must know regarding {subject}.",
            "The first protection guarantees an immediate refund or replacement for defective purchases.",
            "The second rule renders unfair clauses and hidden contract penalties legally null and void.",
            "The third safeguard ensures statutory timelines to dispute unauthorized charges and protect your money.",
            "Knowing these essential legal rules keeps you protected in everyday transactions.",
            "Have you ever had to enforce any of these consumer rights? Share your story below.",
        ]

    if family == "product":
        if is_tr:
            return [
                f"{subject} konusunda günlük hayatınızı kolaylaştıracak ve fark yaratacak harika çözümler var.",
                "İlk çözüm, sık karşılaşılan pratik bir sorunu saniyeler içinde zahmetsizce ortadan kaldırıyor.",
                "İkinci araç, çalışma alanınızdaki verimliliği artırarak zamandan ve enerjiden tasarruf sağlıyor.",
                "Üçüncü yöntem ise ergonomik yapısıyla en zorlu rutinleri bile son derece konforlu hale getiriyor.",
                "Bu yenilikçi yaklaşımlar sayesinde günlük işlerinizi çok daha keyifli ve hızlı tamamlayabilirsiniz.",
                "Peki sizce bu pratik çözümlerden hangisi en çok işinize yarardı? Yorumlarda buluşalım.",
            ]
        return [
            f"Here are practical solutions that solve everyday problems and upgrade your routine in {subject}.",
            "The first item solves a frustrating daily hassle in just a few seconds with zero effort.",
            "The second tool maximizes efficiency in your daily workflow while saving precious time.",
            "The third solution provides ergonomic comfort for demanding tasks you deal with every day.",
            "These practical innovations completely elevate your daily lifestyle and productivity.",
            "Which of these practical finds would you use most? Let us know in the comments.",
        ]

    if family == "mystery" or nid in ("1_scary_stories", "18_true_crime_cases", "26_unsolved_mysteries"):
        if is_tr:
            return [
                f"{subject} dosyasında yıllardır cevapsız kalan ve araştırmacıları şaşırtan karanlık bir sır yatıyor.",
                "Olay günü kayıtlara geçen ilk ifadeler sıradan görünse de zaman çizelgesinde açıklanamayan bir boşluk vardı.",
                "Görgü tanıklarının anlattıkları birbiriyle çelişirken, olay yerinde bulunan tek bir iz şüpheleri bambaşka yöne çekti.",
                "Arşiv belgeleri incelendiğinde, daha önce hiç dikkat çekmeyen kritik bir ipucu gün yüzüne çıktı.",
                "Uzmanlar bu kanıtı modern yöntemlerle yeniden analiz ettiğinde alışılagelmiş tüm teoriler çöktü.",
                "En tuhaf detay ise olayın hemen öncesinde kaydedilen son sinyalin beklenmedik bir noktadan gelmesiydi.",
                "Resmi raporlar dosyayı kapatsa da cevapsız kalan bu ayrıntı gizemi daha da derinleştirdi.",
                "İki farklı ihtimal öne çıkıyor: Ya planlı bir şaşırtmaca vardı ya da kimsenin tahmin etmediği bir tesadüf yaşandı.",
                "Bugün bile bu vakayı inceleyenler aynı sorunun etrafında dönüp duruyor.",
                "Peki sizce bu gizemin arkasındaki asıl gerçek neydi? Teorinizi yorumlara yazın.",
            ]
        return [
            f"Inside the case of {subject} lies an unsettling mystery that has baffled investigators for years.",
            "Initial reports from that day seemed routine, yet a critical gap in the timeline remained unexplained.",
            "While witness accounts contradicted one another, a single trace at the scene shifted every suspicion.",
            "When archival records were re-examined, a previously overlooked clue finally surfaced.",
            "Forensic specialists re-evaluated that evidence with modern tools, overturning the accepted theory.",
            "The strangest detail was the final signal recorded moments before the incident vanished.",
            "Even after official inquiries closed, that unanswered anomaly kept the case alive.",
            "Two possibilities remain: a deliberate misdirection or an extraordinary chain of coincidences.",
            "To this day, researchers examining the file come back to the exact same question.",
            "What do you think really happened behind the scenes? Share your theory in the comments.",
        ]

    if family == "entertainment" or nid in ("2_reddit_stories", "20_whatsapp_chat_story", "20_whatsapp_confessions"):
        if is_tr:
            return [
                f"{subject} başlığıyla paylaşılan bu gerçek hikaye okuyan herkesi ikiye böldü.",
                "Her şey sıradan bir günde gelen beklenmedik bir mesajla başladı ve ortam bir anda gerildi.",
                "İlk başta küçük bir yanlış anlaşılma sanılsa da karşı tarafın tepkisi olayı bambaşka bir boyuta taşıdı.",
                "Araya giren yakın çevre durumu yatıştırmak yerine tartışmayı daha da alevlendirdi.",
                "Asıl kırılma noktası, saklanan o küçük sırrın herkesin içinde ortaya çıkmasıyla yaşandı.",
                "O andan sonra kimse geri adım atmadı ve taraflar kendi haklılığını savunmaya devam etti.",
                "Paylaşımın altına binlerce yorum yağdı; kimileri anlatanı desteklerken kimileri sertçe eleştirdi.",
                "Sonradan gelen güncelleme ise olayın hiç tahmin edilmeyen bir uzlaşmayla sonuçlandığını gösterdi.",
                "Günlük hayatta sıkça karşılaşılan bu sınır problemi aslında iletişimin ne kadar kritik olduğunu kanıtlıyor.",
                "Siz olsaydınız bu durumda nasıl bir tepki verirdiniz? Yorumlarda fikrinizi paylaşın.",
            ]
        return [
            f"This viral story about {subject} completely divided everyone who read the thread.",
            "It all started on an ordinary afternoon when an unexpected message turned the room tense.",
            "What looked like a minor misunderstanding quickly escalated after a surprisingly harsh reply.",
            "Friends who stepped in to mediate only added fuel to the growing argument.",
            "The real turning point arrived when a hidden detail came out in front of everyone.",
            "Neither side backed down, and each person insisted their boundary was completely reasonable.",
            "Thousands of replies flooded the thread, splitting readers into two fiercely opposing camps.",
            "A final update revealed an unexpected resolution nobody saw coming.",
            "Situations like this show how quickly everyday boundaries can turn into major drama.",
            "How would you have handled this exact situation? Drop your take in the comments.",
        ]

    if (family == "quiz" and nid != "9_five_facts") or nid in (
        "3_would_you_rather",
        "4_quiz_trivia",
        "10_riddles_brain_teasers",
        "29_optical_illusions_iq",
        "33_would_you_rather_extremes",
    ):
        if is_tr:
            return [
                f"{subject} testinde çoğu insan ilk soruda yanılıyor; sadece en dikkatli yüzde beşlik dilim tüm soruları hatasız tamamlayabiliyor!",
                "İlk soru kolay görünüyor ama süreniz dolmadan perde arkasındaki gizli kanıtı yakalamanız gerekiyor.",
                "Üç, iki, bir: Doğru cevap ilk bakışta aklınıza gelen seçenek değil, detayda ortaya çıkan alternatif.",
                "Şimdi zorluk seviyesini biraz artırıyoruz; ikinci soruda zihin hızı ve doğru strateji aynı anda test ediliyor.",
                "Birçok kişi burada acele ettiği için hata yapıyor, oysa kelimelerin arasındaki fark gerçeği ele veriyor.",
                "Süre bitti: Bu aşamayı da doğru bildiyseniz ortalamanın çok üzerindesiniz demektir.",
                "Son ve en zor soruya geçmeden önce dikkatinizi tamamen ekrandaki kurala odaklayın.",
                "Bu final sorusunu sadece keskin gözlem gücüne sahip olanlar üç saniye içinde çözebiliyor.",
                "Doğru yanıt tam olarak beklediğinizden farklı bir mantık bağlantısına dayanıyor.",
                "Kaçta kaç yaptığınızı yorumlara yazın ve bakalım kimler tam puan almayı başardı!",
            ]
        return [
            f"Only the sharpest five percent can pass this {subject} challenge without a single mistake.",
            "The first question looks simple, but you need to spot the hidden clue before the timer runs out.",
            "Three, two, one: the correct answer is not the obvious first guess, but the detail hiding in plain sight.",
            "Now let us raise the difficulty; round two tests both speed and lateral thinking.",
            "Most players miss this one by rushing, yet the wording itself gives away the solution.",
            "Time is up: if you got that right, you are already ahead of the crowd.",
            "Before the final boss question, lock your focus onto the subtle pattern on screen.",
            "Only observers with razor-sharp attention solve this last puzzle in under three seconds.",
            "The answer hinges on a clever logical twist most people overlook.",
            "Drop your score in the comments and see who managed a perfect run!",
        ]

    if family == "kids" or nid in ("30_kids_bedtime_stories", "31_kids_fun_facts"):
        if is_tr:
            return [
                f"Bugün birlikte {subject} dünyasında neşeli ve merak dolu harika bir yolculuğa çıkıyoruz.",
                "Küçük kahramanımız sabah güneş doğarken bahçede parlayan rengarenk bir iz fark etti.",
                "Merakla o izi takip ettiğinde karşısına sevimli dostları ve yepyeni bir bilmece çıktı.",
                "Hep birlikte yardımlaşarak doğanın içindeki bu eğlenceli sırrı adım adım çözmeye başladılar.",
                "Yol boyunca her bir çiçek, bulut ve rüzgar onlara doğanın ne kadar uyumlu çalıştığını gösterdi.",
                "Karşılarına çıkan küçük engeli sabırla ve nezaketle aşmayı başardılar.",
                "Günün sonunda öğrendikleri en güzel şey, paylaşmanın ve merak etmenin her kapıyı açtığıydı.",
                "Gökyüzü tatlı bir akşam rengine bürünürken tüm dostlar mutlulukla evlerine döndü.",
                "Doğadaki her canlı gibi onlar da birlikte çalışmanın verdiği huzurla günü tamamladı.",
                "Peki bu sevimli macerada sizin en sevdiğiniz bölüm hangisi oldu? Birlikte hatırlayalım.",
            ]
        return [
            f"Today we are setting off on a cheerful and curious adventure into the world of {subject}.",
            "As the morning sun rose, our little explorer spotted a colorful trail sparkling in the garden.",
            "Following the clues step by step, friendly companions gathered to solve a playful puzzle together.",
            "By helping one another, they discovered how every part of nature works in harmony.",
            "Along the path, gentle clouds and singing birds showed them a wonderful new surprise.",
            "Whenever a tricky obstacle appeared, patience and kindness helped them find the way forward.",
            "The brightest lesson of the day was that curiosity and teamwork make every journey magical.",
            "As the sky turned soft golden hues, all the friends returned home with warm smiles.",
            "Just like nature around them, they ended the day peaceful, grateful, and ready to dream.",
            "Which moment of this cheerful adventure was your favorite? Let us remember it together.",
        ]

    if is_tr:
        return [
            f"{subject} deyince çoğu insanın aklına tek bir kalıp geliyor; oysa perde arkasında çok daha çarpıcı bir gerçek yatıyor.",
            "Genellikle ilk duyduğumuz bilgiler yüzeysel kalır ve asıl detayı gözden kaçırmamıza neden olur.",
            "Burada kritik nokta sadece görünen sonuç değil, o sonuca götüren görünmez adımlardır.",
            "Günlük hayatın akışı içinde küçük bir ayrıntı gibi dursa da, aslında bütün resmi baştan sona değiştirir.",
            "Birçok insan bu noktada yanılıyor; çünkü bu bahsettiğimiz durum, derinlerdeki başka bir sebebin doğrudan sonucudur.",
            "Bunu bir kez fark ettiğinizde, aynı konuya bir daha asla eski gözle bakamazsınız.",
            "İşin özü oldukça net: Yüzeysel gürültüye kapılmak yerine, asıl farkı yaratan o kilit noktaya odaklanmak gerekir.",
            "Bir dahaki sefere benzer bir iddia veya durumla karşılaştığınızda, hemen karar vermeden önce bu ayrımı hatırlayın.",
            "Çünkü en doğru bakış açısı aceleyle değil, meselenin kökenini sakince kavrayarak elde edilir.",
            "Ve işte tam bu yüzden, ilk başta basit görünen o ayrıntı, aslında tüm hikayenin en can alıcı noktasıydı.",
        ]
    return [
        f"When people mention {subject}, they usually reduce it to a simple label, but the real story runs much deeper.",
        "Most first impressions are incomplete, shaped by assumptions rather than what actually happened.",
        "The real insight is not the visible outcome, but the hidden sequence of events leading up to it.",
        "In everyday life it might look like a minor detail, yet that single element shifts the entire balance.",
        f"This is where the common narrative fails: what is called {subject} is actually the direct effect of a much larger cause.",
        "Once you grasp that dynamic, you can never look at this situation the same way again.",
        "The lesson is simple: cutting through the surface noise reveals what truly drives the outcome.",
        "Next time you encounter this claim, pause for a moment and compare it against the underlying facts.",
        "Because true understanding is never rushed; it comes from examining the quiet mechanics beneath the surface.",
        "And that is precisely why the detail everyone overlooked was the key all along.",
    ]



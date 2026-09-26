import React, { createContext, useContext, useState } from 'react';

export type LanguageCode = 'en' | 'hi' | 'sat' | 'or' | 'gon';

export interface LanguageOption {
  code: LanguageCode;
  name: string;
  nativeName: string;
  region: string;
}

export const SUPPORTED_LANGUAGES: LanguageOption[] = [
  { code: 'en', name: 'English', nativeName: 'English', region: 'National' },
  { code: 'hi', name: 'Hindi', nativeName: 'हिन्दी (Hindi)', region: 'National / Central' },
  { code: 'sat', name: 'Santhali', nativeName: 'ᱥᱟᱱᱛᱟᱲᱤ (Santali)', region: 'Jharkhand / Odisha / WB' },
  { code: 'or', name: 'Odia', nativeName: 'ଓଡ଼ିଆ (Odia)', region: 'Odisha' },
  { code: 'gon', name: 'Gondi', nativeName: 'गोंडी (Gondi)', region: 'MP / Chhattisgarh' },
];

const TRANSLATIONS: Record<LanguageCode, Record<string, string>> = {
  en: {
    portalTitle: 'ScholarSetu',
    portalSubtitle: 'Ministry of Tribal Affairs | Government of India',
    studentView: 'Student Portal',
    ministryView: 'Ministry Console',
    familyMode: 'Family View',
    studentBadge: 'Post-Matric ST Scholarship',
    dbtStatusTitle: 'DBT Guardian Status',
    dbtSeeded: 'NPCI Seeded & Verified',
    dbtActionRequired: 'Bank Account Seeding Pending at NPCI',
    pathwayTitle: 'Auto-Renewed Application Ready',
    pathwayDesc: 'Class 10 Matriculation verified via DigiLocker. ST Caste Attestation reused from verified repository.',
    passportTitle: 'Scholarship Verification Passport',
    passportSubtitle: 'Asymmetric Ed25519 Signed • Offline Verifiable Document',
    verifyOnce: 'Single Verification, Universal Portability',
    askJago: 'JAGO Assistance Desk',
    sanctioned: 'Sanctioned Amount',
    credited: 'Credited to Bank (PFMS)',
    pendingRelease: 'Pending Disbursement',
    offlineVerifyBtn: 'Print / Download Official Passport',
    sovereignBadge: 'On-Premise GovCloud • DPDP Act 2023 Compliant',
    simulateDbtFix: 'Re-Verify Bank Seeding (NPCI Gateway)',
    dbtSuccessAlert: 'DBT Validation Successful: Bank account active on NPCI NACH Mapper. Ready for PFMS credit.',
  },
  hi: {
    portalTitle: 'स्कॉलरसेतु',
    portalSubtitle: 'जनजातीय कार्य मंत्रालय | भारत सरकार',
    studentView: 'छात्र पोर्टल',
    ministryView: 'मंत्रालय कंसोल',
    familyMode: 'पारिवारिक विवरण',
    studentBadge: 'मैट्रिकोत्तर जनजाति छात्रवृत्ति',
    dbtStatusTitle: 'डीबीटी गार्जियन स्थिति',
    dbtSeeded: 'आधार से जुड़ा एवं सक्रिय बैंक खाता',
    dbtActionRequired: 'आवश्यक कार्रवाई: बैंक खाते में आधार सीडिंग बाकी है',
    pathwayTitle: 'नवीनीकरण आवेदन तैयार',
    pathwayDesc: 'डिजिलॉकर से 10वीं का अंकपत्र स्वतः सत्यापित। अनुसूचित जनजाति प्रमाणपत्र पुनः उपयोग किया गया।',
    passportTitle: 'डिजिटल छात्रवृत्ति पासपोर्ट (सत्यापित)',
    passportSubtitle: 'Ed25519 डिजिटल हस्ताक्षर • बिना इंटरनेट सत्यापन',
    verifyOnce: 'एक बार सत्यापन, सर्वत्र उपयोग',
    askJago: 'जागो सहायता केंद्र',
    sanctioned: 'स्वीकृत राशि',
    credited: 'बैंक खाते में जमा (PFMS)',
    pendingRelease: 'भुगतान प्रक्रियाधीन',
    offlineVerifyBtn: 'आधिकारिक पासपोर्ट प्रिंट / डाउनलोड करें',
    sovereignBadge: 'स्थानीय डेटा संप्रभुता • डेटा संरक्षण अधिनियम 2023',
    simulateDbtFix: 'बैंक आधार सीडिंग पुनः परीक्षण (NPCI)',
    dbtSuccessAlert: 'डीबीटी सत्यापन सफल: बैंक खाता एनपीसीआई मैपर पर सक्रिय एवं प्रमाणित है।',
  },
  sat: {
    portalTitle: 'ᱥᱠᱚᱞᱟᱨᱥᱮᱛᱩ',
    portalSubtitle: 'ᱟᱹᱫᱤᱵᱟᱹᱥᱤ ᱢᱚᱱᱛᱨᱟᱲᱚᱭ | ᱥᱤᱧᱚᱛ ᱥᱚᱨᱠᱟᱨ',
    studentView: 'ᱯᱟᱹᱴᱷᱩᱣᱟᱹ ᱯᱳᱨᱴᱟᱞ',
    ministryView: 'ᱢᱚᱱᱛᱨᱟᱲᱚᱭ ᱠᱚᱱᱥᱳᱞ',
    familyMode: 'ᱜᱷᱟᱨᱚᱸᱡᱽ ᱧᱮᱞ',
    studentBadge: 'ᱢᱮᱴᱨᱤᱠ ᱛᱟᱭᱚᱢ ᱟᱹᱫᱤᱵᱟᱹᱥᱤ ᱥᱠᱚᱞᱟᱨᱥᱤᱯ',
    dbtStatusTitle: 'DBT ᱜᱟᱨᱰᱤᱭᱟᱱ ᱦᱟᱞᱚᱛ',
    dbtSeeded: 'ᱟᱫᱷᱟᱨ ᱡᱚᱲᱟᱣ ᱥᱟᱹᱛ ᱟᱠᱟᱱᱟ',
    dbtActionRequired: 'ᱫᱚᱨᱠᱟᱨ: ᱵᱮᱸᱠ ᱮᱠᱟᱣᱩᱱᱴ ᱨᱮ ᱟᱫᱷᱟᱨ ᱥᱤᱰᱤᱝ ᱠᱚᱨᱟᱣ ᱢᱮ',
    pathwayTitle: 'ᱟᱯᱱᱟᱨ ᱛᱮ ᱥᱠᱚᱞᱟᱨᱥᱤᱯ ᱥᱟᱯᱲᱟᱣ ᱟᱠᱟᱱᱟ',
    pathwayDesc: '᱑᱐ ᱟᱱᱟᱜ ᱵᱤᱱᱤᱰ ᱨᱮᱱᱟᱜ ᱢᱟᱨᱠᱥᱤᱴ ᱧᱟᱢ ᱟᱠᱟᱱᱟ ᱾ ᱡᱟᱹᱛᱤ ᱥᱟᱠᱟᱢ ᱟᱨᱦᱚᱸ ᱵᱮᱵᱷᱟᱨ ᱮᱱᱟ ᱾',
    passportTitle: 'ᱠᱨᱤᱯᱴᱳᱜᱽᱨᱟᱯᱷᱤᱠ ᱥᱠᱚᱞᱟᱨᱥᱤᱯ ᱯᱟᱥᱯᱳᱨᱴ',
    passportSubtitle: 'Ed25519 ᱥᱩᱦᱤ • ᱵᱤᱱᱟ ᱤᱱᱴᱟᱨᱱᱮᱴ ᱛᱮ ᱯᱚᱨᱠᱷᱟᱣ',
    verifyOnce: 'ᱢᱤᱫ ᱫᱷᱟᱣ ᱯᱚᱨᱠᱷᱟᱣ, ᱡᱚᱛᱚ ᱴᱷᱟᱶ ᱨᱮ ᱵᱮᱵᱷᱟᱨ',
    askJago: 'JAGO ᱜᱚᱲᱚᱭᱤᱡ',
    sanctioned: 'ᱢᱚᱧᱡᱩᱨ ᱴᱟᱠᱟ',
    credited: 'ᱵᱮᱸᱠ ᱨᱮ ᱡᱚᱢᱟ (PFMS)',
    pendingRelease: 'ᱵᱟᱹᱠᱤ ᱢᱮᱱᱟᱜ-ᱟ',
    offlineVerifyBtn: 'ᱥᱚᱨᱠᱟᱨᱤ ᱯᱟᱥᱯᱳᱨᱴ ᱪᱷᱟᱯᱟ / ᱰᱟᱣᱩᱱᱞᱳᱰ ᱢᱮ',
    sovereignBadge: 'ᱥᱤᱧᱚᱛᱤᱭᱟᱹ ᱥᱟᱹᱨᱤ ᱮᱟᱭᱤ • ᱰᱟᱴᱟ ᱯᱨᱟᱭᱵᱷᱮᱥᱤ ᱟᱹᱭᱤᱱ ᱒᱐᱒᱓',
    simulateDbtFix: 'ᱵᱮᱸᱠ ᱟᱫᱷᱟᱨ ᱡᱚᱲᱟᱣ ᱯᱚᱨᱠᱷᱟᱣ (NPCI)',
    dbtSuccessAlert: 'DBT ᱵᱮᱵᱚᱥᱛᱟ ᱥᱟᱹᱛ ᱮᱱᱟ: ᱵᱮᱸᱠ ᱮᱠᱟᱣᱩᱱᱴ ᱱᱤᱛ ᱴᱷᱤᱠ ᱜᱮᱭᱟ ᱾',
  },
  or: {
    portalTitle: 'ସ୍କଲାରସେତୁ',
    portalSubtitle: 'ଜନଜାତି ବ୍ୟାପାର ମନ୍ତ୍ରଣାଳୟ | ଭାରତ ସରକାର',
    studentView: 'ଛାତ୍ର ପୋର୍ଟାଲ',
    ministryView: 'ମନ୍ତ୍ରଣାଳୟ କନସୋଲ',
    familyMode: 'ପାରିବାରିକ ବିବରଣୀ',
    studentBadge: 'ମାଟ୍ରିକୋତ୍ତର ଜନଜାତି ଛାତ୍ରବୃତ୍ତି',
    dbtStatusTitle: 'DBT ଗାର୍ଡିଆନ୍ ସ୍ଥିତି',
    dbtSeeded: 'ଆଧାର ସଂଯୋଗ ସଫଳ ଏବଂ ସକ୍ରିୟ',
    dbtActionRequired: 'ଆବଶ୍ୟକ କାର୍ଯ୍ୟାନୁଷ୍ଠାନ: ବ୍ୟାଙ୍କ ଖାତାରେ ଆଧାର ସିଡିଙ୍ଗ୍ ବାକି ଅଛି',
    pathwayTitle: 'ସ୍ୱୟଂଚାଳିତ ନବୀକରଣ ପ୍ରସ୍ତୁତ',
    pathwayDesc: 'ଡିଜିଲକରରୁ ଦଶମ ଶ୍ରେଣୀ ମାର୍କସିଟ୍ ଯାଞ୍ଚ ହୋଇଛି । ଜନଜାତି ପ୍ରମାଣପତ୍ର ପୁନଃବ୍ୟବହାର ହୋଇଛି ।',
    passportTitle: 'ଡିଜିଟାଲ୍ ସ୍କଲାରସିପ୍ ପାସପୋର୍ଟ',
    passportSubtitle: 'Ed25519 ସ୍ୱାକ୍ଷରିତ • ବିନା ଇଣ୍ଟରନେଟ୍ ଯାଞ୍ଚ',
    verifyOnce: 'ଥରେ ଯାଞ୍ଚ, ସର୍ବତ୍ର ବ୍ୟବହାର',
    askJago: 'ଜାଗୋ ସହାୟତା କେନ୍ଦ୍ର',
    sanctioned: 'ମଞ୍ଜୁର ରାଶି',
    credited: 'ବ୍ୟାଙ୍କରେ ଜମା (PFMS)',
    pendingRelease: 'ଦେୟ ବାକି ଅଛି',
    offlineVerifyBtn: 'ସରକାରୀ ପାସପୋର୍ଟ ପ୍ରିଣ୍ଟ / ᱰାଉନଲୋଡ୍ କରନ୍ତୁ',
    sovereignBadge: 'ସାର୍ବଭୌମ ସ୍ଥାନୀୟ ଏଆଇ • ଡିପିଡିପି ଆଇନ ୨୦୨୩',
    simulateDbtFix: 'ବ୍ୟାଙ୍କ ଆଧାର ସିଡିଙ୍ଗ୍ ଯାଞ୍ଚ (NPCI)',
    dbtSuccessAlert: 'DBT ସମାଧାନ ସଫଳ: ବ୍ୟାଙ୍କ ଖାତା ବର୍ତ୍ତମାନ NPCI ରେ ସକ୍ରିୟ ଅଛି ।',
  },
  gon: {
    portalTitle: 'स्कॉलरसेतु',
    portalSubtitle: 'जनजातीय कार्य मंत्रालय | भारत सरकार',
    studentView: 'छात्र दर्शन',
    ministryView: 'मंत्रालय कंसोल',
    familyMode: 'कुटुंब विवरण',
    studentBadge: 'मैट्रिकोत्तर छात्रवृत्ति',
    dbtStatusTitle: 'DBT देखरेख',
    dbtSeeded: 'आधार खाता जुड़ल बा',
    dbtActionRequired: 'सूचना: बैंक खाता म आधार जोड़ना जरूरी बा',
    pathwayTitle: 'नवीनीकरण तैयार बा',
    pathwayDesc: '१०वीं अंकपत्र सत्यापित बा। जनजाति प्रमाण पत्र फेरु उपयोग भइल।',
    passportTitle: 'डिजिटल छात्रवृत्ति पासपोर्ट',
    passportSubtitle: 'Ed25519 सुरक्षित • बिना इंटरनेट जांच',
    verifyOnce: 'एक बेर जांच, सब जगह मान्य',
    askJago: 'जागो सहायता केंद्र',
    sanctioned: 'मंजूर राशि',
    credited: 'बैंक म जमा (PFMS)',
    pendingRelease: 'भुगतान बाकी बा',
    offlineVerifyBtn: 'सरकारी पासपोर्ट छापो / डाउनलोड करो',
    sovereignBadge: 'स्थानीय डेटा संप्रभुता • डीपीआरपी कानून २०२३',
    simulateDbtFix: 'बैंक आधार जोड़ परीक्षण (NPCI)',
    dbtSuccessAlert: 'DBT जांच सफल: बैंक खाता अब सक्रिय बा।',
  },
};

interface LanguageContextType {
  language: LanguageCode;
  setLanguage: (lang: LanguageCode) => void;
  currentOption: LanguageOption;
  t: (key: string) => string;
}

const LanguageContext = createContext<LanguageContextType>({
  language: 'en',
  setLanguage: () => {},
  currentOption: SUPPORTED_LANGUAGES[0],
  t: (key: string) => key,
});

export const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [language, setLanguageState] = useState<LanguageCode>(() => {
    const saved = localStorage.getItem('scholarsetu_lang') as LanguageCode;
    return saved && TRANSLATIONS[saved] ? saved : 'en';
  });

  const setLanguage = (lang: LanguageCode) => {
    setLanguageState(lang);
    localStorage.setItem('scholarsetu_lang', lang);
  };

  const currentOption = SUPPORTED_LANGUAGES.find((l) => l.code === language) || SUPPORTED_LANGUAGES[0];

  const t = (key: string): string => {
    const langDict = TRANSLATIONS[language] || TRANSLATIONS.en;
    return langDict[key] || TRANSLATIONS.en[key] || key;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, currentOption, t }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => useContext(LanguageContext);

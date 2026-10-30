import React from 'react';
import {SafeAreaView, View, Text, TouchableOpacity, StyleSheet, ScrollView} from 'react-native';
import type {Language} from '../i18n/translations';

const copy = {
ru:{tag:'ЕДИНАЯ СИСТЕМА ГОСТИНИЦЫ',title:'Работа становится проще',description:'Задачи, номера и рабочие уведомления — в одном приложении.',step1:'Получите приглашение от администратора',step2:'Откройте персональную ссылку или отсканируйте QR-код',step3:'Войдите в свой рабочий аккаунт',unavailable:'Подключение к реальной гостинице будет доступно после проверки мобильной авторизации.',demo:'Открыть демонстрацию',warning:'Демонстрация не подключена к MARINA SMART. Все задачи вымышленные.'},
ky:{tag:'МЕЙМАНКАНАНЫН БИРДИКТҮҮ СИСТЕМАСЫ',title:'Ишти жеңилдетебиз',description:'Тапшырмалар, бөлмөлөр жана билдирүүлөр — бир колдонмодо.',step1:'Администратордон чакыруу алыңыз',step2:'Шилтемени ачыңыз же QR-кодду сканерлеңиз',step3:'Жумуш аккаунтуңузга кириңиз',unavailable:'Чыныгы мейманканага туташуу мобилдик авторизация текшерилгенден кийин иштейт.',demo:'Демонстрацияны ачуу',warning:'Демо MARINA SMART менен байланышкан эмес. Бардык тапшырмалар ойдон чыгарылган.'},
en:{tag:'ONE HOTEL WORKSPACE',title:'Work made simple',description:'Tasks, rooms and staff notifications in one app.',step1:'Get an invitation from your hotel administrator',step2:'Open your invite link or scan its QR code',step3:'Sign in to your staff account',unavailable:'Live hotel connection is disabled until mobile authentication passes security review.',demo:'Explore demonstration',warning:'This demo is not connected to MARINA SMART. All tasks are fictional.'}
} as const;
export default function Welcome({language,onDemo}: {language:Language;onDemo:()=>void}) {
 const t=copy[language];
 return <SafeAreaView style={styles.screen}><ScrollView contentContainerStyle={styles.container}>
  <View style={styles.brand}><Text style={styles.logo}>MARINA <Text style={styles.teal}>STAFF</Text></Text><Text style={styles.badge}>PREVIEW · DEMO ONLY</Text></View>
  <View style={styles.hero}><Text style={styles.tag}>{t.tag}</Text><Text style={styles.title}>{t.title}</Text><Text style={styles.subtitle}>{t.description}</Text></View>
  <View style={styles.panel}>{([t.step1,t.step2,t.step3] as const).map((step,index)=><View style={styles.step} key={index}><View style={styles.bubble}><Text style={styles.bubbleText}>{index+1}</Text></View><Text style={styles.stepText}>{step}</Text></View>)}</View>
  <View style={styles.notice}><Text style={styles.noticeText}>🔒 {t.unavailable}</Text></View>
  <TouchableOpacity accessibilityRole="button" style={styles.button} onPress={onDemo}><Text style={styles.buttonText}>{t.demo} →</Text></TouchableOpacity>
  <Text style={styles.finePrint}>{t.warning}</Text>
 </ScrollView></SafeAreaView>;
}
const styles=StyleSheet.create({screen:{flex:1,backgroundColor:'#F1F7F8'},container:{padding:24,paddingTop:35,paddingBottom:45},brand:{marginBottom:50},logo:{fontSize:24,fontWeight:'900',letterSpacing:1,color:'#153E45'},teal:{color:'#0C9993'},badge:{fontSize:10,fontWeight:'800',color:'#AD753C',marginTop:5},hero:{marginBottom:35},tag:{fontSize:10,fontWeight:'900',letterSpacing:2,color:'#0C9993',marginBottom:12},title:{fontSize:39,fontWeight:'900',lineHeight:45,color:'#143B45'},subtitle:{fontSize:16,color:'#5C7882',lineHeight:25,marginTop:17},panel:{backgroundColor:'#FFFFFF',borderRadius:24,padding:20,marginBottom:20},step:{flexDirection:'row',gap:15,alignItems:'center',marginVertical:12},bubble:{width:33,height:33,borderRadius:17,backgroundColor:'#DCF3F0',alignItems:'center',justifyContent:'center'},bubbleText:{fontSize:14,fontWeight:'900',color:'#078F88'},stepText:{flex:1,fontSize:13,lineHeight:20,color:'#254D57',fontWeight:'600'},notice:{borderRadius:14,backgroundColor:'#FFF3E4',padding:15,marginBottom:24},noticeText:{color:'#835D36',fontSize:12,lineHeight:19},button:{backgroundColor:'#087F80',padding:19,borderRadius:16,alignItems:'center'},buttonText:{fontSize:16,fontWeight:'800',color:'#FFF'},finePrint:{textAlign:'center',fontSize:11,color:'#7B9197',lineHeight:17,marginTop:15}});

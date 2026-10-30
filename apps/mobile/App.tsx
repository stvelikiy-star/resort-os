import React, {useMemo, useState} from 'react';
import {SafeAreaView, ScrollView, StatusBar, StyleSheet, Text, TouchableOpacity, View} from 'react-native';
import {Role, roles, sampleTasks, summary, transitionTask} from './src/domain/tasks';
import {Language, roleNames, translations} from './src/i18n/translations';
import {APP_MODE} from './src/config/mode';
import Welcome from './src/screens/Welcome';

type Tab = 'home' | 'tasks' | 'profile';
const roleIcons: Record<Role, string> = {HOUSEKEEPING:'🧹',REPAIR:'🔧',RECEPTION:'🛎️',KITCHEN:'🍳',WAITER:'🍽️',MANAGER:'📊'};
export default function App() {
 const [lang, setLang] = useState<Language>('ru');
 const [demoOpened, setDemoOpened] = useState(false);
 const [role, setRole] = useState<Role>('HOUSEKEEPING');
 const [tab, setTab] = useState<Tab>('home');
 const [tasks, setTasks] = useState(sampleTasks);
 const [expanded, setExpanded] = useState<string | null>(null);
 const t = translations[lang];
 const selected = useMemo(() => tasks.filter(task => task.role === role), [tasks,role]);
 const counts = useMemo(() => summary(tasks,role),[tasks,role]);
 if (!demoOpened) return <Welcome language={lang} onDemo={() => setDemoOpened(true)} />;
 return <SafeAreaView style={styles.root}>
  <StatusBar barStyle="dark-content"/>
  <View style={styles.top}>
   <View><Text style={styles.brand}>MARINA <Text style={styles.teal}>STAFF</Text></Text><Text style={styles.demo}>{APP_MODE} · {t.demo}</Text></View>
   <View style={styles.languages}>{(['ru','ky','en'] as Language[]).map(item=><TouchableOpacity accessibilityRole="button" accessibilityLabel={item} key={item} onPress={()=>setLang(item)} style={[styles.language,item===lang&&styles.languageActive]}><Text style={[styles.langText,item===lang&&styles.white]}>{item.toUpperCase()}</Text></TouchableOpacity>)}</View>
  </View>
  <ScrollView contentContainerStyle={styles.content}>
   <Text style={styles.overline}>MARINA SMART · STAFF</Text>
   <Text style={styles.heading}>{tab==='profile'?t.myProfile:tab==='tasks'?t.myTasks:t.hello}</Text>
   <Text style={styles.warning}>{t.warning}</Text>
   {tab==='profile'?<View style={styles.card}>
    <Text style={styles.cardTitle}>{t.hotel}</Text><Text style={styles.description}>{roleIcons[role]} {t[roleNames[role]]}</Text>
    <Text style={styles.description}>{t.language}: {lang.toUpperCase()}</Text>
    <Text style={styles.note}>🔒 {t.demo}</Text>
   </View>:<>
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.roles}>
     {roles.map(item=><TouchableOpacity accessibilityRole="button" key={item} style={[styles.roleChip,item===role&&styles.roleActive]} onPress={()=>{setRole(item);setExpanded(null)}}><Text style={[styles.roleText,item===role&&styles.white]}>{roleIcons[item]} {t[roleNames[item]]}</Text></TouchableOpacity>)}
    </ScrollView>
    <View style={styles.stats}>
     <View style={styles.stat}><Text style={styles.statValue}>{counts.active}</Text><Text style={styles.statLabel}>{t.active}</Text></View>
     <View style={styles.stat}><Text style={styles.statValue}>{counts.done}</Text><Text style={styles.statLabel}>{t.done}</Text></View>
    </View>
    <Text style={styles.section}>{t.today}</Text>
    {selected.length===0&&<Text style={styles.description}>{t.allDone}</Text>}
    {selected.map(task=><View style={styles.card} key={task.id}>
     <TouchableOpacity accessibilityRole="button" accessibilityLabel={task.title} onPress={()=>setExpanded(expanded===task.id?null:task.id)}>
      <View style={styles.cardHeader}><Text style={styles.room}>{t.room}: {task.room}</Text><Text style={styles.state}>{task.status==='NEW'?t.new:task.status==='IN_PROGRESS'?t.progress:t.completed}</Text></View>
      <Text style={styles.cardTitle}>{task.title}</Text>
      {task.priority==='urgent'&&<Text style={styles.urgent}>● {t.urgent}</Text>}
     </TouchableOpacity>
     {(expanded===task.id||tab==='tasks')&&<Text style={styles.description}>{task.detail}</Text>}
     {task.status!=='DONE'&&<TouchableOpacity accessibilityRole="button" accessibilityLabel={task.status==='NEW'?t.start:t.finish} style={styles.button} onPress={()=>setTasks(current=>transitionTask(current,task.id,role))}><Text style={styles.buttonText}>{task.status==='NEW'?t.start:t.finish} →</Text></TouchableOpacity>}
    </View>)}
   </>}
  </ScrollView>
  <View style={styles.nav}>{(['home','tasks','profile'] as Tab[]).map(item=><TouchableOpacity accessibilityRole="button" key={item} style={styles.navItem} onPress={()=>setTab(item)}><Text style={[styles.navLabel,tab===item&&styles.navSelected]}>{item==='home'?'⌂ ':item==='tasks'?'☷ ':'◉ '}{t[item]}</Text></TouchableOpacity>)}</View>
 </SafeAreaView>;
}
const styles=StyleSheet.create({
 root:{flex:1,backgroundColor:'#F4F8F9'},
 top:{backgroundColor:'#FFFFFF',paddingHorizontal:20,paddingVertical:18,borderBottomWidth:1,borderColor:'#DFEAED',flexDirection:'row',justifyContent:'space-between',alignItems:'center'},
 brand:{fontSize:20,fontWeight:'900',letterSpacing:1,color:'#153A44'},teal:{color:'#0A9996'},demo:{fontSize:9,fontWeight:'800',color:'#B37735',marginTop:4},
 languages:{flexDirection:'row',gap:3},language:{padding:6,borderRadius:7},languageActive:{backgroundColor:'#118985'},langText:{fontSize:10,fontWeight:'800',color:'#557078'},white:{color:'#FFFFFF'},
 content:{padding:20,paddingBottom:35},overline:{fontSize:10,letterSpacing:1.6,color:'#13938E',fontWeight:'900',marginBottom:8},
 heading:{fontSize:30,fontWeight:'800',color:'#173B46',marginBottom:10},warning:{fontSize:12,lineHeight:18,color:'#687E88',marginBottom:18},
 roles:{paddingVertical:4,gap:7,marginBottom:18},roleChip:{backgroundColor:'#FFFFFF',borderRadius:18,borderWidth:1,borderColor:'#D7E5E8',paddingVertical:11,paddingHorizontal:13},roleActive:{backgroundColor:'#0A8986',borderColor:'#0A8986'},roleText:{fontSize:12,fontWeight:'800',color:'#2E5863'},
 stats:{flexDirection:'row',gap:10,marginBottom:25},stat:{flex:1,backgroundColor:'#DFEFEE',padding:20,borderRadius:18},statValue:{fontSize:31,color:'#0B7E7A',fontWeight:'900'},statLabel:{fontSize:12,color:'#5C7B7D',marginTop:4},section:{fontSize:19,fontWeight:'800',color:'#163942',marginBottom:13},
 card:{backgroundColor:'#FFFFFF',borderWidth:1,borderColor:'#E1E9ED',borderRadius:19,padding:17,marginBottom:12},
 cardHeader:{flexDirection:'row',justifyContent:'space-between',marginBottom:12,gap:8},room:{color:'#087E81',fontSize:11,fontWeight:'900'},state:{fontSize:11,color:'#6E8990'},
 cardTitle:{fontSize:17,color:'#193E48',fontWeight:'800',marginBottom:7},description:{color:'#607982',fontSize:13,lineHeight:19,marginVertical:9},urgent:{fontSize:12,fontWeight:'800',color:'#C36D3D',marginBottom:7},note:{fontSize:11,color:'#A06E3D',marginTop:12},
 button:{backgroundColor:'#128E89',borderRadius:12,padding:14,alignItems:'center',marginTop:11},buttonText:{color:'#FFFFFF',fontWeight:'800',fontSize:13},
 nav:{flexDirection:'row',backgroundColor:'#FFFFFF',borderTopWidth:1,borderColor:'#E0E9EC',paddingTop:15,paddingBottom:19},navItem:{flex:1,alignItems:'center'},navLabel:{fontSize:13,color:'#859A9E',fontWeight:'800'},navSelected:{color:'#0E8B87'}
});

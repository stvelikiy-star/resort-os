import React, { useState } from 'react';
import { SafeAreaView, ScrollView, StatusBar, StyleSheet, Text, TouchableOpacity, View } from 'react-native';

type Role = 'HOUSEKEEPING' | 'REPAIR' | 'RECEPTION';
type Task = { id: string; room: string; title: string; status: 'NEW' | 'IN_PROGRESS' | 'DONE'; role: Role };
const tasks: Task[] = [
  { id: 'demo-clean-1', room: '101', title: 'Уборка после выезда', status: 'NEW', role: 'HOUSEKEEPING' },
  { id: 'demo-clean-2', room: '205', title: 'Проверить комплект белья', status: 'IN_PROGRESS', role: 'HOUSEKEEPING' },
  { id: 'demo-repair-1', room: '302', title: 'Проверить кондиционер', status: 'NEW', role: 'REPAIR' },
  { id: 'demo-reception-1', room: '110', title: 'Подготовить номер к заезду', status: 'NEW', role: 'RECEPTION' },
];
const labels: Record<Role, string> = { HOUSEKEEPING: 'Горничная', REPAIR: 'Техник', RECEPTION: 'Ресепшен' };
const statusLabels: Record<Task['status'], string> = { NEW: 'Новое', IN_PROGRESS: 'В работе', DONE: 'Выполнено' };
export default function App() {
  const [role, setRole] = useState<Role>('HOUSEKEEPING');
  const [items, setItems] = useState<Task[]>(tasks);
  const [tab, setTab] = useState<'home' | 'tasks' | 'profile'>('home');
  const visible = items.filter(task => task.role === role);
  const active = visible.filter(task => task.status !== 'DONE');
  const advance = (id: string) => setItems(old => old.map(task => task.id === id
    ? { ...task, status: task.status === 'NEW' ? 'IN_PROGRESS' : 'DONE' }
    : task));
  return (
    <SafeAreaView style={styles.screen}>
      <StatusBar barStyle="dark-content" />
      <View style={styles.brand}><Text style={styles.brandText}>MARINA <Text style={styles.accent}>STAFF</Text></Text><Text style={styles.demo}>ДЕМО · БЕЗ ПОДКЛЮЧЕНИЯ К PMS</Text></View>
      <ScrollView contentContainerStyle={styles.body}>
        <Text style={styles.eyebrow}>РАБОЧИЙ КАБИНЕТ</Text>
        <Text style={styles.heading}>{tab === 'profile' ? 'Профиль сотрудника' : tab === 'tasks' ? 'Мои задачи' : 'Добрый день!'}</Text>
        <Text style={styles.subheading}>Демонстрационные данные — реальные гостиницы и сотрудники пока не подключены.</Text>
        {tab === 'profile' ? <View style={styles.card}><Text style={styles.title}>Демо-профиль</Text><Text style={styles.detail}>Роль: {labels[role]}</Text><Text style={styles.detail}>Гостиница: демо-объект</Text><Text style={styles.detail}>Авторизация и подключение по QR — следующий этап.</Text></View> : <>
          <View style={styles.roleRow}>{(Object.keys(labels) as Role[]).map(item =>
            <TouchableOpacity accessibilityRole="button" key={item} style={[styles.chip, role === item && styles.selected]} onPress={() => setRole(item)}><Text style={[styles.chipText, role === item && styles.selectedText]}>{labels[item]}</Text></TouchableOpacity>
          )}</View>
          <View style={styles.metrics}><View style={styles.metric}><Text style={styles.number}>{active.length}</Text><Text style={styles.muted}>Активных задач</Text></View><View style={styles.metric}><Text style={styles.number}>{visible.filter(x => x.status === 'DONE').length}</Text><Text style={styles.muted}>Выполнено</Text></View></View>
          <Text style={styles.section}>Задачи на сегодня</Text>
          {visible.map(task => <View key={task.id} style={styles.card}><View style={styles.taskTop}><Text style={styles.room}>НОМЕР {task.room}</Text><Text style={styles.state}>{statusLabels[task.status]}</Text></View><Text style={styles.title}>{task.title}</Text>{task.status !== 'DONE' && <TouchableOpacity accessibilityRole="button" style={styles.action} onPress={() => advance(task.id)}><Text style={styles.actionText}>{task.status === 'NEW' ? 'Принять задачу' : 'Завершить (демо)'}</Text></TouchableOpacity>}</View>)}
        </>}
      </ScrollView>
      <View style={styles.nav}>{([{id:'home',text:'Главная'},{id:'tasks',text:'Задачи'},{id:'profile',text:'Профиль'}] as const).map(item => <TouchableOpacity key={item.id} accessibilityRole="button" style={styles.navButton} onPress={() => setTab(item.id)}><Text style={[styles.navText, tab === item.id && styles.navActive]}>{item.text}</Text></TouchableOpacity>)}</View>
    </SafeAreaView>
  );
}
const styles = StyleSheet.create({
  screen:{flex:1,backgroundColor:'#F5F8FA'},brand:{backgroundColor:'#FFFFFF',paddingHorizontal:24,paddingTop:20,paddingBottom:16,borderBottomWidth:1,borderColor:'#E7EFF2'},
  brandText:{fontSize:21,fontWeight:'900',letterSpacing:1.3,color:'#12333C'},accent:{color:'#12A6A1'},demo:{fontSize:10,color:'#AF6931',marginTop:5,fontWeight:'800'},
  body:{padding:22,paddingBottom:40},eyebrow:{fontSize:11,fontWeight:'800',letterSpacing:1.7,color:'#159B99',marginBottom:9},
  heading:{fontSize:29,fontWeight:'800',color:'#153640'},subheading:{color:'#627C84',lineHeight:21,marginTop:10,marginBottom:20},
  roleRow:{flexDirection:'row',gap:7,flexWrap:'wrap',marginBottom:19},chip:{borderColor:'#CBDDE1',borderWidth:1,borderRadius:20,paddingVertical:9,paddingHorizontal:12,backgroundColor:'#fff'},
  selected:{backgroundColor:'#087F80',borderColor:'#087F80'},chipText:{color:'#325660',fontSize:12,fontWeight:'700'},selectedText:{color:'#FFFFFF'},
  metrics:{flexDirection:'row',gap:12,marginBottom:26},metric:{flex:1,backgroundColor:'#E3F4F2',padding:17,borderRadius:17},
  number:{fontSize:30,color:'#137C80',fontWeight:'900'},muted:{color:'#648288',marginTop:4,fontSize:12},
  section:{fontSize:19,fontWeight:'800',color:'#1A3A43',marginBottom:14},card:{backgroundColor:'#fff',padding:19,borderRadius:18,marginBottom:12,borderWidth:1,borderColor:'#E3EBEF'},
  taskTop:{flexDirection:'row',justifyContent:'space-between',marginBottom:12},room:{color:'#178E8A',fontWeight:'800',fontSize:11},state:{color:'#6E838A',fontSize:12},
  title:{fontSize:17,color:'#183C46',fontWeight:'700',marginBottom:14},detail:{color:'#4F6770',marginBottom:10},action:{borderRadius:11,backgroundColor:'#128B89',padding:13,alignItems:'center'},actionText:{color:'#FFFFFF',fontWeight:'800'},
  nav:{flexDirection:'row',backgroundColor:'#fff',borderTopWidth:1,borderColor:'#E3EBEF',paddingVertical:14},navButton:{flex:1,alignItems:'center'},navText:{fontSize:13,color:'#85979B',fontWeight:'700'},navActive:{color:'#0B8783'}
});

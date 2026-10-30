export type Role = 'HOUSEKEEPING' | 'REPAIR' | 'RECEPTION' | 'KITCHEN' | 'WAITER' | 'MANAGER';
export type TaskStatus = 'NEW' | 'IN_PROGRESS' | 'DONE';
export type Task = { id: string; room: string; title: string; status: TaskStatus; role: Role; detail: string; priority: 'normal' | 'urgent' };
export const roles: Role[] = ['HOUSEKEEPING','REPAIR','RECEPTION','KITCHEN','WAITER','MANAGER'];
export const sampleTasks: Task[] = [
 {id:'demo-h1',room:'101',title:'Уборка после выезда',detail:'Сменить бельё, проверить ванную и принадлежности.',status:'NEW',role:'HOUSEKEEPING',priority:'urgent'},
 {id:'demo-h2',room:'205',title:'Проверка номера',detail:'Проверить полотенца, воду и комплектацию.',status:'IN_PROGRESS',role:'HOUSEKEEPING',priority:'normal'},
 {id:'demo-r1',room:'302',title:'Кондиционер не охлаждает',detail:'Провести диагностику и сообщить о результате.',status:'NEW',role:'REPAIR',priority:'urgent'},
 {id:'demo-re1',room:'110',title:'Подготовить заселение',detail:'Проверить готовность номера до прибытия.',status:'NEW',role:'RECEPTION',priority:'normal'},
 {id:'demo-k1',room:'Кухня',title:'Подготовить заказ №24',detail:'Завтрак для двух гостей.',status:'NEW',role:'KITCHEN',priority:'normal'},
 {id:'demo-w1',room:'Стол 4',title:'Подача заказа',detail:'Передать готовые блюда гостям.',status:'NEW',role:'WAITER',priority:'normal'},
 {id:'demo-m1',room:'Корпус А',title:'Проверка смены',detail:'Проверить выполнение текущих задач.',status:'NEW',role:'MANAGER',priority:'normal'}
];
export function transitionTask(tasks: readonly Task[], id: string, role: Role): Task[] {
 return tasks.map(task => {
  if (task.id !== id || task.role !== role || task.status === 'DONE') return task;
  return {...task, status: task.status === 'NEW' ? 'IN_PROGRESS' : 'DONE'};
 });
}
export function summary(tasks: readonly Task[], role: Role) {
 const selected = tasks.filter(item => item.role === role);
 return {active: selected.filter(item => item.status !== 'DONE').length,done:selected.filter(item => item.status === 'DONE').length};
}

import { useSession } from '../state/session';
const strings = {
  ru: {
    overview: 'Обзор', reception: 'Сегодня', pms: 'Шахматка', inbox: 'Чаты', dining: 'Питание',
    tasks: 'Задачи', rooms: 'Номера', requests: 'Ремонт', admin: 'Команда', profile: 'Профиль',
    unavailable: 'В этой среде нет подтверждённых рабочих данных. Подключите защищённый адрес отеля.',
    denied: 'Раздел недоступен по правам текущей роли.', empty: 'Нет данных', retry: 'Повторить', loading: 'Загрузка…',
    today: 'Сегодня', needsReply: 'Нужен ответ', all: 'Все', inboxTitle: 'Единый Inbox', note: 'Внутренняя заметка (не отправляется гостю)',
    notePlaceholder: 'Комментарий для команды', saveNote: 'Сохранить заметку', claim: 'Взять диалог',
    resolve: 'Закрыть диалог', reopen: 'Открыть диалог', assigned: 'Ответственный', noSend: 'Отправка WhatsApp пока не подключена к серверу. Заметки видны только сотрудникам.',
    revenue: 'Поступления сегодня', debt: 'Долг по активным броням', occupancy: 'Занято номеров', arrivals: 'Заезды',
    departures: 'Выезды', urgent: 'Срочные задачи', paymentsNotProfit: 'Поступления не являются прибылью',
    available: 'Доступность', noRooms: 'Номеров нет', clean: 'Готов', dirty: 'Уборка', tech: 'Ремонт',
    bookings: 'Бронирования', checkIn: 'Заселить', checkOut: 'Выселить', confirm: 'Подтвердить действие?',
    confirmed: 'Сервер подтвердил изменение', unknown: 'Результат операции неизвестен. Сверьте статус в платформе; автоматически не повторяйте.',
    choose: 'Выберите', start: 'Начало', end: 'Конец', next: 'Следующая неделя', previous: 'Предыдущая неделя',
    orders: 'Заказы кухни', tables: 'Столы', status: 'Статус', take: 'Взять', guest: 'Гость', readOnly: 'Только просмотр',
    more: 'Детали', close: 'Закрыть', senderBlocked: 'Нет серверной отправки WhatsApp',
  },
  en: {
    overview: 'Overview', reception: 'Today', pms: 'PMS grid', inbox: 'Chats', dining: 'Dining',
    tasks: 'Tasks', rooms: 'Rooms', requests: 'Repairs', admin: 'Team', profile: 'Profile',
    unavailable: 'No verified live hotel data in this environment. Connect a secure hotel address.',
    denied: 'You do not have permission for this section.', empty: 'No records', retry: 'Retry', loading: 'Loading…',
    today: 'Today', needsReply: 'Needs reply', all: 'All', inboxTitle: 'Unified Inbox', note: 'Internal note (not sent to guest)',
    notePlaceholder: 'Note for the team', saveNote: 'Save note', claim: 'Claim conversation',
    resolve: 'Resolve', reopen: 'Reopen', assigned: 'Assigned to', noSend: 'WhatsApp sending is not connected on the server. Notes are internal only.',
    revenue: 'Payments received today', debt: 'Outstanding active bookings', occupancy: 'Rooms occupied', arrivals: 'Arrivals',
    departures: 'Departures', urgent: 'Urgent tasks', paymentsNotProfit: 'Payments received are not profit',
    available: 'Availability', noRooms: 'No rooms', clean: 'Clean', dirty: 'Cleaning', tech: 'Maintenance',
    bookings: 'Reservations', checkIn: 'Check in', checkOut: 'Check out', confirm: 'Confirm this action?',
    confirmed: 'Server confirmed', unknown: 'Operation outcome unknown. Verify on the platform before retrying.',
    choose: 'Choose', start: 'Start', end: 'End', next: 'Next week', previous: 'Previous week',
    orders: 'Kitchen orders', tables: 'Tables', status: 'Status', take: 'Claim', guest: 'Guest', readOnly: 'View only',
    more: 'Details', close: 'Close', senderBlocked: 'WhatsApp outbound not configured on server',
  },
  kg: {
    overview: 'Сереп', reception: 'Бүгүн', pms: 'Брондор', inbox: 'Чаттар', dining: 'Тамактануу',
    tasks: 'Тапшырмалар', rooms: 'Бөлмөлөр', requests: 'Оңдоо', admin: 'Команда', profile: 'Профиль',
    unavailable: 'Бул чөйрөдө ырасталган маалымат жок. Мейманкананын коопсуз дарегине туташыңыз.',
    denied: 'Бул бөлүмгө укугуңуз жок.', empty: 'Маалымат жок', retry: 'Кайталоо', loading: 'Жүктөлүүдө…',
    today: 'Бүгүн', needsReply: 'Жооп керек', all: 'Баары', inboxTitle: 'Бирдиктүү Inbox', note: 'Ички эскертүү (конокко жөнөтүлбөйт)',
    notePlaceholder: 'Команда үчүн эскертүү', saveNote: 'Эскертүүнү сактоо', claim: 'Сүйлөшүүнү алуу',
    resolve: 'Жабуу', reopen: 'Кайра ачуу', assigned: 'Жооптуу', noSend: 'WhatsApp жөнөтүү серверде азырынча иштебейт. Эскертүүлөр ички.',
    revenue: 'Бүгүн алынган төлөмдөр', debt: 'Активдүү брондордун карызы', occupancy: 'Ээлеген бөлмөлөр', arrivals: 'Келүүлөр',
    departures: 'Кетүүлөр', urgent: 'Шашылыш иштер', paymentsNotProfit: 'Алынган төлөм пайда эмес',
    available: 'Жеткиликтүүлүк', noRooms: 'Бөлмө жок', clean: 'Даяр', dirty: 'Тазалоо', tech: 'Оңдоо',
    bookings: 'Брондор', checkIn: 'Жайгаштыруу', checkOut: 'Чыгаруу', confirm: 'Ырастайсызбы?',
    confirmed: 'Сервер ырасталды', unknown: 'Натыйжа белгисиз. Кайталоодон мурда платформада текшериңиз.',
    choose: 'Тандоо', start: 'Башталышы', end: 'Аягы', next: 'Кийинки жума', previous: 'Мурунку жума',
    orders: 'Ашкана заказдары', tables: 'Үстөлдөр', status: 'Статус', take: 'Алуу', guest: 'Конок', readOnly: 'Көрүү гана',
    more: 'Маалымат', close: 'Жабуу', senderBlocked: 'Серверде WhatsApp жөнөтүү жок',
  },
};
export type MobileCopy = typeof strings.ru;
export function useMobileCopy(): MobileCopy {
  const { locale } = useSession();
  return strings[locale === 'en' ? 'en' : locale === 'kg' ? 'kg' : 'ru'];
}

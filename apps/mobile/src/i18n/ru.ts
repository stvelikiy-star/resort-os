export const ru = {
  common: { appName: 'MARINA STAFF', cancel: 'Отмена', save: 'Сохранить', back: 'Назад', next: 'Далее', done: 'Готово', retry: 'Повторить', loading: 'Загрузка…', empty: 'Пока ничего нет', demo: 'ДЕМО-РЕЖИМ · данные не из PMS', room: 'Номер', all: 'Все' },
  nav: { tasks: 'Задачи', rooms: 'Номера', requests: 'Заявки', admin: 'Админ', profile: 'Профиль' },
  connect: {
    title: 'Подключение к отелю', subtitle: 'Каждый отель — отдельное защищённое подключение. Данные отелей не смешиваются.',
    addHotel: 'Добавить отель', code: 'Код приглашения или адрес', codePh: 'например, marina-bishkek', scan: 'Сканировать QR', demoHotels: 'Демо-отели',
    secureOnly: 'Допускаются только HTTPS-адреса', invalid: 'Неверный код или адрес', connected: 'Подключено', choose: 'Выберите отель', noSecrets: 'Приложение не хранит ключей сервера',
  },
  login: { title: 'Вход сотрудника', username: 'Логин', password: 'Пароль', signIn: 'Войти', demoRole: 'Демо: войти как', wrong: 'Неверный логин или пароль', hotel: 'Отель', change: 'Сменить отель' },
  roles: { OWNER: 'Владелец', MANAGER: 'Менеджер', RECEPTION: 'Ресепшн', AGENT: 'Агент', MAID: 'Горничная', TECHNICIAN: 'Техник', STORE_STAFF: 'Магазин', COOK: 'Повар', WAITER: 'Официант', CONTENT_MANAGER: 'Контент', BEACH_PARTNER: 'Пляж' },
  tasks: { title: 'Мои задачи', today: 'Сегодня', open: 'Новые', inProgress: 'В работе', inspection: 'На проверке', done: 'Готово', start: 'Начать', finish: 'Завершить', toInspection: 'Сдать на проверку', approve: 'Принять', reject: 'Вернуть в работу', urgent: 'Срочно', high: 'Высокий', normal: 'Обычный', low: 'Низкий', none: 'Задач нет — отдыхайте', progress: 'Выполнено', quick: 'Быстрые действия', types: { HOUSEKEEPING: 'Уборка', MAINTENANCE: 'Ремонт', GUEST_REQUEST: 'Запрос гостя' } },
  rooms: { title: 'Номера', state: { UNKNOWN: 'Не определён', CLEAN: 'Чисто', DIRTY: 'Грязно', IN_INSPECTION: 'Проверка', TECH_BLOCK: 'Тех. блок' }, floor: 'Этаж', guest: 'Гость', checkout: 'Выезд', arrival: 'Заезд', vacant: 'Свободен', openTasks: 'Открытые задачи', setState: 'Статус номера', history: 'История', notes: 'Заметки' },
  hk: { title: 'Чек-лист уборки', BED_LINEN: 'Постельное бельё', BATHROOM: 'Ванная комната', SURFACES: 'Поверхности и пол', AMENITIES: 'Принадлежности', FINAL_CHECK: 'Финальная проверка', photo: 'Фото-отчёт', addPhoto: 'Добавить фото', photoSoon: 'Загрузка фото появится после серверного API', comment: 'Комментарий', submit: 'Сдать номер', incomplete: 'Отметьте все пункты', sent: 'Номер сдан на проверку' },
  mt: { title: 'Заявка на ремонт', newRequest: 'Новая заявка', category: 'Категория', priority: 'Приоритет', describe: 'Что случилось?', describePh: 'Кратко опишите проблему', send: 'Отправить заявку', sent: 'Заявка создана', cats: { PLUMBING: 'Сантехника', ELECTRIC: 'Электрика', HVAC: 'Кондиционер', FURNITURE: 'Мебель', OTHER: 'Другое' }, list: 'Заявки', block: 'Заблокировать номер' },
  admin: { title: 'Управление', inspection: 'Очередь проверки', staff: 'Сотрудники на смене', assign: 'Назначить', unassigned: 'Не назначено', stats: 'Сводка дня', occupancy: 'Загрузка', dirty: 'Грязных', blocked: 'Заблокировано', overdue: 'Просрочено', forbidden: 'Нет доступа к этому разделу' },
  profile: { title: 'Профиль', language: 'Язык', theme: 'Тема', system: 'Системная', light: 'Светлая', dark: 'Тёмная', hotel: 'Отель', role: 'Роль', signOut: 'Выйти', switchHotel: 'Сменить отель', about: 'О приложении', version: 'Версия', mode: 'Режим данных', modeDemo: 'Демонстрационный', roleSoon: 'Рабочее место для вашей роли в мобильном приложении готовится', modeLive: 'Рабочий сервер' },
  errors: { generic: 'Что-то пошло не так', offline: 'Нет связи с сервером', forbidden: 'Недостаточно прав', notFound: 'Не найдено' },
};
export type Dict = typeof ru;

import type { Locale } from './index';

/** Presentation-only wording for the nine synthetic fixture tasks.
 * LIVE task descriptions always use the original server text unchanged.
 */
const tasks: Record<Locale, Record<string, string>> = {
  ru: {
    t1:'Уборка после выезда', t2:'Генеральная уборка', t3:'Проверка номера после уборки',
    t4:'Кондиционер не охлаждает', t5:'Течь крана в ванной', t6:'Дополнительные полотенца',
    t7:'Уборка завершена', t8:'Подготовить номер к заселению', t9:'Проверить освещение',
  },
  kg: {
    t1:'Конок кеткенден кийинки тазалоо', t2:'Кылдат тазалоо', t3:'Тазалоодон кийин бөлмөнү текшерүү',
    t4:'Кондиционер муздатпай жатат', t5:'Жуунучу бөлмөдөгү крандан суу агып жатат', t6:'Кошумча сүлгүлөр',
    t7:'Тазалоо аяктады', t8:'Бөлмөнү конокко даярдоо', t9:'Жарыкты текшерүү',
  },
  en: {
    t1:'Clean after checkout', t2:'Deep cleaning', t3:'Post-cleaning room inspection',
    t4:'Air conditioner not cooling', t5:'Bathroom tap leaking', t6:'Extra towels',
    t7:'Cleaning completed', t8:'Prepare room for arrival', t9:'Check room lighting',
  },
  kz: {
    t1:'Қонақ шыққаннан кейін тазалау', t2:'Күрделі тазалау', t3:'Тазалаудан кейін бөлмені тексеру',
    t4:'Кондиционер салқындатпай тұр', t5:'Жуынатын бөлмедегі шүмек ағып тұр', t6:'Қосымша сүлгілер',
    t7:'Тазалау аяқталды', t8:'Бөлмені қонаққа дайындау', t9:'Жарықты тексеру',
  },
};
export function demoTaskTitle(id: string, locale: Locale, fallback: string): string {
  return tasks[locale][id] ?? fallback;
}

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import styles from "./ChefProduction.module.css";
import KitchenStock from "./KitchenStock";

type Ingredient = { name: string; unit: "KG" | "L" | "PCS"; quantity_per_portion: string };
type Recipe = { version: number; status: "DRAFT" | "APPROVED"; is_sample: boolean; ingredients: Ingredient[] };
type Dish = { id: string; name_ru: string; recipe: Recipe | null };
type Requirements = {
  contains_sample_data: boolean; is_complete: boolean;
  items: Array<{ name: string; unit: string; planned_quantity: string; prepared_quantity: string; remaining_quantity: string }>;
  missing_recipes: Array<{ name_ru: string; service_date: string }>; inventory_deducted?: boolean;
};
type Targets = {
  items: Array<{ id: string; name_ru: string; planned_quantity: number; prepared_quantity: number; remaining_quantity: number }>;
  ingredient_requirements?: Requirements;
};

async function api(path: string, init?: RequestInit) {
  const response = await fetch("/core/api/v1/kitchen" + path, { cache:"no-store", ...init });
  const body = await response.json();
  if (!response.ok) {
    throw new Error(typeof body.detail === "string" ? body.detail : body.detail?.code || "Проверьте рецептуру и обновите данные");
  }
  return body;
}

function RecipeEditor({ dish, reload }: { dish: Dish; reload: () => Promise<void> }) {
  const [ingredients, setIngredients] = useState<Ingredient[]>(dish.recipe?.ingredients ??
    [{ name:"", unit:"KG", quantity_per_portion:"" }]);
  const [approved, setApproved] = useState(dish.recipe?.status === "APPROVED");
  const [sample, setSample] = useState(dish.recipe?.is_sample ?? true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const change = (index: number, patch: Partial<Ingredient>) =>
    setIngredients(rows => rows.map((row, i) => i === index ? { ...row, ...patch } : row));
  const save = async () => {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      await api("/menu/" + dish.id + "/recipe", {
        method:"PUT", headers:{"Content-Type":"application/json"},
        body:JSON.stringify({expected_version:dish.recipe?.version ?? 0,
          status:approved?"APPROVED":"DRAFT", is_sample:sample, ingredients}),
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось сохранить рецептуру");
    } finally {
      await reload();
      setBusy(false);
    }
  };
  return <div data-testid="kitchen-recipe-editor" className={styles.controls}>
    <h3>Нормы на одну порцию</h3>
    {ingredients.map((ingredient,index) => <div key={index}>
      <label>Продукт<input disabled={busy} aria-label="Продукт" value={ingredient.name} maxLength={120}
        onChange={e=>change(index,{name:e.target.value})}/></label>
      <label>Количество на порцию<input disabled={busy} aria-label="Количество на порцию" type="number" min="0.000001" max="1000" step="0.000001"
        value={ingredient.quantity_per_portion} onChange={e=>change(index,{quantity_per_portion:e.target.value})}/></label>
      <label>Единица<select disabled={busy} value={ingredient.unit} onChange={e=>change(index,{unit:e.target.value as Ingredient["unit"]})}>
        <option>KG</option><option>L</option><option>PCS</option>
      </select></label>
      {ingredients.length>1 ? <button disabled={busy} onClick={()=>setIngredients(rows=>rows.filter((_,i)=>i!==index))}>Убрать продукт</button> : null}
    </div>)}
    <button disabled={busy||ingredients.length>=100} onClick={()=>setIngredients(rows=>[...rows,{name:"",unit:"KG",quantity_per_portion:""}])}>Добавить продукт</button>
    <label><input disabled={busy} type="checkbox" checked={approved} onChange={e=>setApproved(e.target.checked)}/>Использовать в расчёте</label>
    <label><input disabled={busy} type="checkbox" checked={sample} onChange={e=>setSample(e.target.checked)}/>Учебные нормы — замените своими</label>
    <button disabled={busy || ingredients.some(x=>!x.name.trim() || Number(x.quantity_per_portion)<=0)}
      onClick={()=>void save()}>Сохранить рецептуру</button>
    {error ? <p role="alert" className={styles.error}>{error}</p> : null}
  </div>;
}

export default function KitchenIngredients({ fromDate, throughDate, userRole }: {
  fromDate: string; throughDate: string; userRole: string;
}) {
  const [targets, setTargets] = useState<Targets | null>(null);
  const [menu, setMenu] = useState<Dish[]>([]);
  const [dishId, setDishId] = useState("");
  const [error, setError] = useState("");
  const generation = useRef(0);
  const load = useCallback(async () => {
    const request = ++generation.current;
    try {
      const [targetBody, menuBody] = await Promise.all([
        api("/production-targets?from_date="+encodeURIComponent(fromDate)+"&through_date="+encodeURIComponent(throughDate)),
        api("/production-menu"),
      ]);
      if (request !== generation.current) return;
      setTargets(targetBody);
      setMenu(menuBody.items);
      setError("");
    } catch (e) {
      if (request !== generation.current) return;
      setTargets(null);
      setError(e instanceof Error ? e.message : "Не удалось загрузить продукты");
    }
  }, [fromDate,throughDate]);
  useEffect(() => {
    void load();
    const timer = window.setInterval(()=>void load(),30000);
    return ()=>{generation.current++;window.clearInterval(timer);};
  }, [load]);
  const data = targets?.ingredient_requirements;
  const dish = menu.find(item=>item.id===dishId);
  return <section className={styles.day} data-testid="kitchen-ingredient-requirements">
    <div className={styles.head}><h2>Продукты по рецептурам</h2><button onClick={()=>void load()}>Обновить продукты</button></div>
    {error ? <p role="alert" className={styles.error}>{error}</p> : null}
    {targets?.items.map(item=><p key={item.id}>{item.name_ru} · План: {item.planned_quantity} · Приготовлено: {item.prepared_quantity} · Осталось: {item.remaining_quantity}</p>)}
    {data?.contains_sample_data ? <p className={styles.notice}>Учебные нормы — замените своими</p> : null}
    {data?.missing_recipes.map((item,index)=><p key={index} className={styles.error}>Нет утверждённой рецептуры: {item.name_ru} · {item.service_date}</p>)}
    {data?.items.map(item=><div key={item.name+item.unit} className={styles.lines}>
      <strong>{item.name} · {item.unit}</strong>
      <p>На весь план: {item.planned_quantity} · На приготовленные порции: {item.prepared_quantity} · На оставшиеся порции: {item.remaining_quantity}</p>
    </div>)}
    {data?.is_complete && !data.items.length ? <p>Нет потребности на выбранный период</p> : null}
    <p>{data?.is_complete ? (data.inventory_deducted ? "Фактический расход приготовленных порций списан со склада." : "Потребность по рецептурам рассчитана. Списание производится отдельно.") : "Заполните рецептуры для полного расчёта потребности."}</p>
    {userRole==="OWNER" || userRole==="MANAGER" ? <>
      <label>Блюдо для рецептуры<select aria-label="Блюдо для рецептуры" value={dishId} onChange={e=>setDishId(e.target.value)}>
        <option value="">Выберите блюдо</option>
        {menu.map(item=><option key={item.id} value={item.id}>{item.name_ru}</option>)}
      </select></label>
      {dish ? <RecipeEditor key={dish.id+":"+(dish.recipe?.version ?? 0)} dish={dish} reload={load}/> : null}
    </> : null}
    <KitchenStock fromDate={fromDate} throughDate={throughDate} userRole={userRole}/>
  </section>;
}

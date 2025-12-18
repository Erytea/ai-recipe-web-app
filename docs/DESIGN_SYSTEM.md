# Дизайн-система AI Recipe Bot

## 🎨 Цветовая палитра

### Основные цвета (из color.pdf и существующих стилей)

#### Красная тема (RINGO - текущая основная тема)
```css
--ringo-red: #c41e3a;
--ringo-red-dark: #8b1528;
--ringo-red-light: #e63950;
```

#### Синяя палитра (из Bright blue.pdf)
```css
--bright-blue-50: #EFF1FD;
--bright-blue-100: #E1DFFB;
--bright-blue-200: #D6DCFF;
--bright-blue-300: #B6C8F9;
--bright-blue-400: #A3AEF5;
--bright-blue-500: #8494F1;
--bright-blue-600: #576CED;
--bright-blue-700: #2B50ED;
--bright-blue-800: #3736D7;
--bright-blue-900: #3D425C;
```

#### Дополнительные цвета (из color.pdf)
```css
--high-flavor: /* Основной цвет для акцентов */
--flavor: /* Вторичный акцентный цвет */
--motto-grey-300: /* Серый для текста */
--high-furple-50: #F2F2FF;  /* Фиолетовый оттенок */
--high-orange-50: #FFF2E8;  /* Оранжевый оттенок */
--high-yellow-30: #FFFBF0;  /* Желтый оттенок */
--high-mid-50: #F0F8F0;     /* Зеленый оттенок */
```

### Семантические цвета

#### Светлая тема (Light Theme)
```css
--primary: var(--ringo-red);
--primary-dark: var(--ringo-red-dark);
--primary-light: var(--ringo-red-light);

--secondary: var(--bright-blue-500);
--secondary-dark: var(--bright-blue-700);
--secondary-light: var(--bright-blue-300);

--accent: var(--high-orange-50);
--success: var(--high-mid-50);
--warning: var(--high-yellow-30);
--error: var(--ringo-red);

--text-primary: #1a1a1a;
--text-secondary: #666666;
--text-disabled: #cccccc;

--background: #ffffff;
--surface: #f8f9fa;
--surface-variant: #e9ecef;
```

## 📝 Типографика

### Шрифты
- **Основной шрифт**: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif
- **Моноширинный**: Для кода и чисел

### Размеры текста (из Typography.pdf)

#### Заголовки
```css
--text-display-large: 3rem;    /* 48px - для главных заголовков */
--text-display-medium: 2.5rem; /* 40px */
--text-headline-large: 2rem;   /* 32px */
--text-headline-medium: 1.75rem; /* 28px */
--text-title-large: 1.375rem;   /* 22px */
--text-title-medium: 1rem;      /* 16px */
```

#### Основной текст
```css
--text-body-large: 1rem;       /* 16px */
--text-body-medium: 0.875rem;  /* 14px */
--text-body-small: 0.75rem;    /* 12px */
```

#### Метки и кнопки
```css
--text-label-large: 0.875rem;  /* 14px */
--text-label-medium: 0.75rem;  /* 12px */
--text-label-small: 0.625rem;  /* 10px */
```

### Вес шрифта
```css
--font-weight-light: 300;
--font-weight-regular: 400;
--font-weight-medium: 500;
--font-weight-bold: 700;
--font-weight-black: 900;
```

### Высота строки
```css
--line-height-tight: 1.2;
--line-height-normal: 1.5;
--line-height-relaxed: 1.8;
```

## 🔘 Компоненты

### Кнопки (Buttons)

#### Основные стили
```css
.btn-primary {
  background-color: var(--primary);
  border-color: var(--primary);
  color: white;
  text-transform: uppercase;
  letter-spacing: 1px;
  font-weight: 500;
  padding: 12px 30px;
  border-radius: 6px;
  transition: all 0.3s ease;
}

.btn-primary:hover {
  background-color: var(--primary-dark);
  border-color: var(--primary-dark);
  transform: translateY(-1px);
}

.btn-outline-primary {
  border-color: var(--primary);
  color: var(--primary);
  background-color: transparent;
}

.btn-outline-primary:hover {
  background-color: var(--primary);
  color: white;
}
```

#### Размеры кнопок
- **Large**: padding: 14px 32px; font-size: 1rem;
- **Medium**: padding: 12px 24px; font-size: 0.875rem;
- **Small**: padding: 8px 16px; font-size: 0.75rem;

### Карточки (Cards)

```css
.card {
  border: none;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.15);
}
```

### Формы (Forms)

#### Поля ввода
```css
.form-control {
  border: 2px solid #e9ecef;
  border-radius: 8px;
  padding: 12px 16px;
  font-size: 1rem;
  transition: border-color 0.3s ease, box-shadow 0.3s ease;
}

.form-control:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(196, 30, 58, 0.1);
}
```

#### Метки
```css
.form-label {
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 8px;
}
```

## 🎯 Лучшие практики (Best Practices)

### 10 эвристик юзабилити Нильсена

1. **Видимость состояния системы** - Показывать прогресс операций
2. **Соответствие между системой и реальным миром** - Использовать понятные термины
3. **Контроль и свобода** - Возможность отмены действий
4. **Последовательность и стандарты** - Единообразие интерфейса
5. **Профилактика ошибок** - Предупреждения перед опасными действиями
6. **Распознавание, а не припоминание** - Видимые опции
7. **Гибкость и эффективность использования** - Горячие клавиши для опытных пользователей
8. **Эстетичный и минималистичный дизайн** - Убирать ненужное
9. **Помощь при ошибках** - Понятные сообщения об ошибках
10. **Справка и документация** - Легкий доступ к помощи

### Material Design принципы

1. **Material is the metaphor** - Материальность как основа
2. **Bold, graphic, intentional** - Смелый, графичный, осознанный
3. **Motion provides meaning** - Анимация несет смысл
4. **Adaptive design** - Адаптивность под все устройства

## 📱 Адаптивный дизайн

### Breakpoints
```css
--breakpoint-xs: 0px;      /* Мобильные */
--breakpoint-sm: 576px;    /* Маленькие планшеты */
--breakpoint-md: 768px;    /* Большие планшеты */
--breakpoint-lg: 992px;    /* Маленькие десктопы */
--breakpoint-xl: 1200px;   /* Большие десктопы */
--breakpoint-xxl: 1400px;  /* Очень большие экраны */
```

### Grid система
- **Container max-width**: 1200px
- **Columns**: 12-колоночная система
- **Gutter**: 24px между колонками

## ♿ Доступность (Accessibility)

### Цветовой контраст
- **Текст на фоне**: Минимум 4.5:1 для обычного текста
- **Крупный текст**: Минимум 3:1 для текста 18pt+
- **Интерактивные элементы**: Минимум 3:1

### Фокус
```css
.focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}
```

### ARIA атрибуты
- Использовать role, aria-label, aria-describedby
- Для динамического контента использовать aria-live

## 🔄 Анимации и переходы

### Длительности
```css
--duration-fast: 150ms;
--duration-normal: 300ms;
--duration-slow: 500ms;
```

### Кривая Безье
```css
--easing-standard: cubic-bezier(0.4, 0.0, 0.2, 1);
--easing-decelerate: cubic-bezier(0.0, 0.0, 0.2, 1);
--easing-accelerate: cubic-bezier(0.4, 0.0, 1, 1);
```

## 📊 Иконки

### Система иконок
- **Bootstrap Icons** - основная библиотека
- **Размер**: 16px, 20px, 24px, 32px
- **Цвет**: Наследуется от текста или используется семантический цвет

### Примеры использования
```html
<!-- Маленькая иконка -->
<i class="bi bi-camera" style="font-size: 16px;"></i>

<!-- Средняя иконка -->
<i class="bi bi-robot" style="font-size: 24px;"></i>

<!-- Большая иконка -->
<i class="bi bi-star-fill" style="font-size: 32px;"></i>
```

## 🛠 Инструменты разработки

### Дизайн
- **Figma** - для создания макетов
- **Material Design Kit** - готовые компоненты

### Код
- **CSS Variables** - для тем и токенов
- **CSS Grid/Flexbox** - для раскладки
- **Bootstrap 5** - как основа компонентов

## 📋 Чек-лист для новых компонентов

- [ ] Соответствует дизайн-системе
- [ ] Адаптивный дизайн
- [ ] Доступность (WCAG 2.1 AA)
- [ ] Темная тема поддержка
- [ ] Кроссбраузерная совместимость
- [ ] Производительность (не более 14kb CSS)
- [ ] Документация в этом файле



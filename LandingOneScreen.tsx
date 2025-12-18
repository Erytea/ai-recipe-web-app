import React from 'react';

// LandingOneScreen - desktop-first one-screen landing для продукта "фото продуктов → рецепт под цель с КБЖУ"
// Размер экрана: 1440×900, 100vh без скролла
// Дизайн-система: цвета и типографика из PDF файлов

const LandingOneScreen: React.FC = () => {
  return (
    <div className="min-h-screen h-screen flex flex-col bg-white overflow-hidden relative">
      {/* Мягкий background wash */}
      <div
        className="absolute inset-0 opacity-30"
        style={{
          background: 'radial-gradient(circle at 80% 20%, #EFF1FD 0%, transparent 50%)',
        }}
      />

      {/* Легкий noise/grain эффект */}
      <div
        className="absolute inset-0 opacity-[0.02]"
        style={{
          backgroundImage: 'url("data:image/svg+xml,%3Csvg viewBox="0 0 256 256" xmlns="http://www.w3.org/2000/svg"%3E%3Cfilter id="noiseFilter"%3E%3CfeTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="4" stitchTiles="stitch"/%3E%3C/filter%3E%3Crect width="100%25" height="100%25" filter="url(%23noiseFilter)"/%3E%3C/svg%3E")',
        }}
      />

      {/* Основной контент */}
      <div className="relative z-10 flex-1 flex flex-col max-w-[1280px] mx-auto px-8 py-12">
        {/* Верхняя секция: Hero слева, Proof справа */}
        <div className="flex-1 flex gap-16 mb-16">
          {/* Левая колонка: Hero */}
          <div className="flex-1 flex flex-col justify-center max-w-[600px]">
            {/* H1 */}
            <h1
              className="text-[32px] leading-[40px] font-semibold mb-6 tracking-normal"
              style={{ color: '#2C2E33', letterSpacing: '0' }}
            >
              Сфоткал продукты.<br />Получил рецепт под цель.
            </h1>

            {/* Subheadline */}
            <p
              className="text-[16px] leading-[24px] mb-12 tracking-normal"
              style={{ color: '#707070', letterSpacing: '0' }}
            >
              КБЖУ считаем сами. Граммовка и шаги сразу.
            </p>

            {/* Кнопки */}
            <div className="flex flex-col gap-4">
              {/* Primary CTA */}
              <button
                className="px-8 py-4 rounded-lg font-medium text-[16px] text-white transition-all duration-300 hover:shadow-lg"
                style={{
                  backgroundColor: '#576CED',
                  letterSpacing: '0',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = '#2B50ED';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = '#576CED';
                }}
              >
                Загрузить фото продуктов
              </button>

              {/* Secondary CTA */}
              <a
                href="#"
                className="text-[14px] font-medium underline transition-colors duration-300 hover:opacity-75"
                style={{ color: '#576CED', letterSpacing: '0' }}
              >
                Посмотреть пример
              </a>
            </div>

            {/* Trust chips */}
            <div className="flex flex-wrap gap-3 mt-8">
              {[
                'Без регистрации',
                '30 сек',
                'КБЖУ автоматически'
              ].map((chip, index) => (
                <div
                  key={index}
                  className="px-4 py-2 rounded-lg text-[12px] font-medium"
                  style={{
                    backgroundColor: '#EFF1FD',
                    border: '1px solid #E1DFFB',
                    color: '#576CED',
                    letterSpacing: '0',
                  }}
                >
                  {chip}
                </div>
              ))}
            </div>
          </div>

          {/* Правая колонка: Proof */}
          <div className="flex-1 flex items-center justify-center">
            <div
              className="w-full max-w-[480px] p-8 rounded-xl border-2"
              style={{
                backgroundColor: '#EFF1FD',
                borderColor: '#E1DFFB',
              }}
            >
              {/* До → После */}
              <div className="flex items-center gap-6 mb-8">
                {/* Фото продуктов (заглушка) */}
                <div className="flex-1">
                  <div className="aspect-square bg-white rounded-lg border-2 border-dashed mb-3 flex items-center justify-center"
                       style={{ borderColor: '#E1DFFB' }}>
                    <div className="text-center">
                      <div className="w-12 h-12 mx-auto mb-2 rounded-full"
                           style={{ backgroundColor: '#EFF1FD' }}>
                        📸
                      </div>
                      <div className="text-[10px]" style={{ color: '#A6A6A6' }}>
                        Фото продуктов
                      </div>
                    </div>
                  </div>
                </div>

                {/* Стрелка с анимацией */}
                <div className="flex-shrink-0">
                  <div className="text-[24px] animate-pulse">→</div>
                </div>

                {/* Результат */}
                <div className="flex-1">
                  <div className="bg-white rounded-lg p-4 border-2"
                       style={{ borderColor: '#E1DFFB' }}>
                    {/* Название блюда */}
                    <h3
                      className="text-[16px] font-semibold mb-3"
                      style={{ color: '#2C2E33', letterSpacing: '0' }}
                    >
                      Паста с овощами
                    </h3>

                    {/* КБЖУ чипсы */}
                    <div className="flex flex-wrap gap-2 mb-4">
                      {[
                        { label: '320 ккал', bg: '#EFF1FD', text: '#576CED' },
                        { label: '25г Б', bg: '#EFF1FD', text: '#576CED' },
                        { label: '12г Ж', bg: '#EFF1FD', text: '#576CED' },
                        { label: '45г У', bg: '#EFF1FD', text: '#576CED' }
                      ].map((chip, index) => (
                        <span
                          key={index}
                          className="px-2 py-1 rounded text-[10px] font-medium"
                          style={{
                            backgroundColor: chip.bg,
                            color: chip.text,
                            letterSpacing: '0',
                          }}
                        >
                          {chip.label}
                        </span>
                      ))}
                    </div>

                    {/* Шаги приготовления */}
                    <div className="space-y-2">
                      {[
                        'Отварите пасту согласно инструкции',
                        'Обжарьте овощи на оливковом масле',
                        'Смешайте и подавайте горячим'
                      ].map((step, index) => (
                        <div key={index} className="flex gap-2">
                          <span
                            className="flex-shrink-0 text-[14px] font-medium"
                            style={{ color: '#2C2E33' }}
                          >
                            {index + 1}.
                          </span>
                          <span
                            className="text-[12px] leading-[16px]"
                            style={{ color: '#2C2E33', letterSpacing: '0' }}
                          >
                            {step}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Дерзкий микро-copy */}
              <p
                className="text-[12px] text-center"
                style={{ color: '#707070', letterSpacing: '0' }}
              >
                Да, даже если на фото бардак.
              </p>

              {/* Акцент линия */}
              <div
                className="w-16 h-0.5 mx-auto mt-4"
                style={{ backgroundColor: '#576CED' }}
              />
            </div>
          </div>
        </div>

        {/* Нижняя полоса: 3 шага */}
        <div className="flex justify-center">
          <div className="grid grid-cols-3 gap-8 max-w-[800px]">
            {[
              { icon: '📸', title: 'Сфоткай продукты' },
              { icon: '🎯', title: 'Выбери цель' },
              { icon: '👨‍🍳', title: 'Получай рецепт' }
            ].map((step, index) => (
              <div key={index} className="text-center">
                <div className="w-16 h-16 mx-auto mb-3 rounded-full flex items-center justify-center text-[24px]">
                  {step.icon}
                </div>
                <h3
                  className="text-[14px] font-medium"
                  style={{ color: '#2C2E33', letterSpacing: '0' }}
                >
                  {step.title}
                </h3>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default LandingOneScreen;

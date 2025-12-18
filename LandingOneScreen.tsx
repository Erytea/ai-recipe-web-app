import React from 'react';

// LandingOneScreen - усиленная конверсия desktop-first one-screen landing
// Усиление CTA, proof-блока, заголовков, микро-движения без новых секций

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
            {/* H1 - усиленный контраст */}
            <h1
              className="text-[36px] leading-[44px] font-bold mb-4 tracking-tight"
              style={{
                color: '#2C2E33',
                letterSpacing: '-0.5px',
                textShadow: '0 1px 2px rgba(0,0,0,0.1)'
              }}
            >
              Сфоткал продукты.<br />Получил рецепт под цель.
            </h1>

            {/* Subheadline - плотнее к H1 */}
            <p
              className="text-[16px] leading-[24px] mb-8 tracking-normal"
              style={{ color: '#707070', letterSpacing: '0' }}
            >
              КБЖУ считаем сами. Граммовка и шаги сразу.
            </p>

            {/* Кнопки - усиленный CTA */}
            <div className="flex flex-col gap-3">
              {/* Primary CTA - доминирующая кнопка */}
              <button
                className="px-10 py-5 rounded-md font-semibold text-[16px] text-white transition-all duration-300 hover:scale-105 hover:shadow-xl"
                style={{
                  backgroundColor: '#576CED',
                  letterSpacing: '0',
                  boxShadow: '0 4px 12px rgba(87, 108, 237, 0.3)',
                  border: 'none',
                  cursor: 'pointer',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = '#2B50ED';
                  e.currentTarget.style.boxShadow = '0 6px 20px rgba(87, 108, 237, 0.5), 0 0 20px rgba(87, 108, 237, 0.2)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = '#576CED';
                  e.currentTarget.style.boxShadow = '0 4px 12px rgba(87, 108, 237, 0.3)';
                }}
              >
                Загрузить фото продуктов
              </button>

              {/* Secondary CTA - ближе, контрастнее */}
              <a
                href="#"
                className="text-[14px] font-semibold transition-all duration-300 hover:scale-105"
                style={{
                  color: '#576CED',
                  letterSpacing: '0',
                  textDecoration: 'none',
                  borderBottom: '1px solid #576CED',
                  paddingBottom: '2px'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = '#2B50ED';
                  e.currentTarget.style.borderBottomColor = '#2B50ED';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = '#576CED';
                  e.currentTarget.style.borderBottomColor = '#576CED';
                }}
              >
                Посмотреть пример
              </a>
            </div>

            {/* Trust chips - сгруппированы плотнее */}
            <div
              className="flex flex-wrap gap-2 mt-6 p-4 rounded-lg transition-all duration-300 hover:shadow-md"
              style={{
                backgroundColor: 'rgba(239, 241, 253, 0.8)',
                border: '1px solid rgba(225, 223, 251, 0.5)',
              }}
            >
              {[
                'Без регистрации',
                '30 сек',
                'КБЖУ автоматически'
              ].map((chip, index) => (
                <div
                  key={index}
                  className="px-3 py-1.5 rounded-md text-[11px] font-medium transition-all duration-200 hover:scale-105"
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

          {/* Правая колонка: Proof - усиленная трансформация */}
          <div className="flex-1 flex items-center justify-center">
            <div
              className="w-full max-w-[480px] p-8 rounded-xl border-2 transition-all duration-300 hover:shadow-lg"
              style={{
                backgroundColor: '#EFF1FD',
                borderColor: '#E1DFFB',
              }}
            >
              {/* До → После - усиленный контраст */}
              <div className="flex items-center gap-6 mb-6">
                {/* Фото продуктов - визуально "хуже" */}
                <div className="flex-1">
                  <div className="aspect-square bg-gray-50 rounded-lg border border-gray-200 mb-3 flex items-center justify-center opacity-75"
                       style={{ borderStyle: 'dashed' }}>
                    <div className="text-center">
                      <div className="w-12 h-12 mx-auto mb-2 rounded-full bg-gray-100 flex items-center justify-center text-2xl">
                        📸
                      </div>
                      <div className="text-[10px] text-gray-500 font-medium">
                        Как есть
                      </div>
                    </div>
                  </div>
                </div>

                {/* Стрелка - усиленная анимация */}
                <div className="flex-shrink-0">
                  <div
                    className="text-[28px] font-bold transition-all duration-500"
                    style={{
                      color: '#576CED',
                      textShadow: '0 2px 4px rgba(0,0,0,0.1)',
                      animation: 'arrowPulse 2s ease-in-out infinite'
                    }}
                  >
                    →
                  </div>
                </div>

                {/* Результат - визуально "лучше" */}
                <div className="flex-1">
                  <div
                    className="bg-white rounded-lg p-4 border-2 transition-all duration-300 hover:shadow-lg hover:scale-105"
                    style={{
                      borderColor: '#576CED',
                      boxShadow: '0 4px 12px rgba(87, 108, 237, 0.15)'
                    }}
                  >
                    {/* Название блюда */}
                    <h3
                      className="text-[16px] font-bold mb-3"
                      style={{ color: '#2C2E33', letterSpacing: '0' }}
                    >
                      Паста с овощами
                    </h3>

                    {/* КБЖУ чипсы - акцент сильнее */}
                    <div className="flex flex-wrap gap-2 mb-4">
                      {[
                        { label: '320 ккал', bg: '#576CED', text: '#FFFFFF' },
                        { label: '25г Б', bg: '#B6C8F9', text: '#2C2E33' },
                        { label: '12г Ж', bg: '#B6C8F9', text: '#2C2E33' },
                        { label: '45г У', bg: '#B6C8F9', text: '#2C2E33' }
                      ].map((chip, index) => (
                        <span
                          key={index}
                          className="px-2 py-1 rounded-md text-[10px] font-bold transition-all duration-200 hover:scale-105"
                          style={{
                            backgroundColor: chip.bg,
                            color: chip.text,
                            letterSpacing: '0',
                            boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
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
                            className="flex-shrink-0 text-[14px] font-bold"
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

              {/* Дерзкий микро-copy - ближе к блоку */}
              <div className="mt-4">
                <p
                  className="text-[12px] text-center font-medium"
                  style={{ color: '#707070', letterSpacing: '0' }}
                >
                  Да, даже если на фото бардак.
                </p>

                {/* Акцент линия */}
                <div
                  className="w-16 h-0.5 mx-auto mt-2"
                  style={{ backgroundColor: '#576CED' }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Нижняя полоса: 3 шага - уменьшенный визуальный вес */}
        <div className="flex justify-center opacity-75">
          <div className="grid grid-cols-3 gap-6 max-w-[700px]">
            {[
              { icon: '📸', title: 'Сфоткай продукты' },
              { icon: '🎯', title: 'Выбери цель' },
              { icon: '👨‍🍳', title: 'Получай рецепт' }
            ].map((step, index) => (
              <div key={index} className="text-center transition-all duration-300 hover:opacity-100">
                <div className="w-12 h-12 mx-auto mb-2 rounded-full flex items-center justify-center text-lg bg-gray-100">
                  {step.icon}
                </div>
                <h3
                  className="text-[13px] font-medium text-gray-600"
                  style={{ letterSpacing: '0' }}
                >
                  {step.title}
                </h3>
              </div>
            ))}
          </div>
        </div>
      </div>

      <style jsx>{`
        @keyframes arrowPulse {
          0%, 100% {
            transform: translateX(0) scale(1);
            opacity: 1;
          }
          50% {
            transform: translateX(3px) scale(1.1);
            opacity: 0.8;
          }
        }
      `}</style>
    </div>
  );
};

export default LandingOneScreen;

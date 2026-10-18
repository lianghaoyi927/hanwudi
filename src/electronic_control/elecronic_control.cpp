#include "main.h"
#include "pstwo.h"

// 物理极性补丁，修正个别电机线接反的转向
int LF_DIR = 1;  // 左前
int RF_DIR = 1;  // 右前
int LB_DIR = -1; // 左后（实测反）
int RB_DIR = -1; // 右后（实测反）

void Delay_ms(uint32_t ms) {
    for(volatile uint32_t i=0; i<ms*2000; i++) { __NOP(); }
}

// 初始化硬件PWM (TIM2, TIM3, TIM4)
void PWM_Init(void) {
    RCC->APB1ENR |= (1 << 0) | (1 << 1) | (1 << 2); 
    
    TIM2->PSC = 3; TIM2->ARR = 999; TIM2->CCMR1 = 0x6868; TIM2->CCMR2 = 0x6868; TIM2->CCER |= 0x1111; TIM2->EGR = 1; TIM2->CR1 |= 0x81;    
    TIM3->PSC = 3; TIM3->ARR = 999; TIM3->CCMR2 = 0x6868; TIM3->CCER |= 0x1100; TIM3->EGR = 1; TIM3->CR1 |= 0x81;
    TIM4->PSC = 3; TIM4->ARR = 999; TIM4->CCMR1 = 0x6868; TIM4->CCER |= 0x0011; TIM4->EGR = 1; TIM4->CR1 |= 0x81;

    // 切换引脚为复用推挽输出 (PA0-3, PB0-1, PB6-7)
    GPIOA->CRL &= 0xFFFF0000; GPIOA->CRL |= 0x0000BBBB; 
    GPIOB->CRL &= 0x00FF0000; GPIOB->CRL |= 0xBBBBBBBB; 
}

int main(void)
{
    RCC->APB2ENR |= (1 << 2) | (1 << 3) | (1 << 4); 

    // 1. 上电防飞车：引脚全设为高阻态（模拟输入）
    GPIOA->CRL &= 0xFFFF0000; 
    GPIOB->CRL &= 0x00FF0000; 

    // 配置 PS2 与 LED 引脚
    GPIOC->CRH &= ~(0xF << 20); GPIOC->CRH |= (0x3 << 20); 
    GPIOB->CRH &= ~(0xFFFF << 16); GPIOB->CRH |= (0x8 << 16); 
    GPIOB->CRH |= (0x3 << 20) | (0x3 << 24) | (0x3 << 28); 

    Delay_ms(1000); 

    uint8_t rx_data[9];
    int SPEED = 800; // PWM 占空比 80%

    // 2. 死锁等待：收到合法数据前，严禁动作
    while (1) {
        // 纯寄存器 SPI 读取数据...
        if (rx_data[0] == 0xFF && rx_data[3] != 0x00 && rx_data[3] != 0xFF) break; 
        Delay_ms(50); 
    }

    // 3. 解除封印，启动 PWM
    PWM_Init();
    
    while (1)
    {
        // SPI 读取手柄数据...
        
        // 4. 防断流保护
        if (rx_data[0] != 0xFF || (rx_data[3] == 0x00 && rx_data[4] == 0x00)) {
            // 停机
            continue;
        }

        // 5. 非标按键映射
        uint8_t is_up    = ((rx_data[3] & 0x40) == 0) || ((rx_data[4] & 0x10) == 0);
        uint8_t is_down  = (rx_data[3] & 0x10) == 0;
        uint8_t is_left  = (rx_data[3] & 0x80) == 0;
        uint8_t is_right = (rx_data[3] & 0x20) == 0;

        int spd_y = 0, spd_x = 0;
        
        // 方向逻辑（根据实车验证对调了前后）
        if (is_up)         spd_y = -SPEED; 
        else if (is_down)  spd_y = SPEED;  
        else if (is_left)  spd_x = -SPEED; 
        else if (is_right) spd_x = SPEED;  

        // 麦轮解算下发
        if (spd_y != 0 || spd_x != 0) {
            // 结合极性补丁写入寄存器
            int lf = (spd_y + spd_x) * LF_DIR;
            int rf = (spd_y - spd_x) * RF_DIR;
            int lb = (spd_y - spd_x) * LB_DIR;
            int rb = (spd_y + spd_x) * RB_DIR;
            // 写 CCR 寄存器...
        } else {
            // 停止电机...
        }
        Delay_ms(20);
    }
}
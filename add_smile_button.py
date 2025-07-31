#!/usr/bin/env python3
"""
為企業網站添加微笑按鈕
"""

import re

def add_smile_button():
    """在登入頁面底部添加微笑按鈕"""
    
    # 讀取文件
    with open('enterprise_web_app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 添加微笑按鈕的樣式
    smile_button_styles = '''
    /* 微笑按鈕容器 */
    .smile-container {
      position: fixed;
      bottom: 20px;
      right: 20px;
      z-index: 1000;
    }
    
    /* 微笑按鈕樣式 */
    .smile-button {
      width: 60px;
      height: 60px;
      border-radius: 50%;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 28px;
      box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
      transition: all 0.3s ease;
      animation: float 3s ease-in-out infinite;
    }
    
    /* 懸停效果 */
    .smile-button:hover {
      transform: scale(1.1);
      box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }
    
    /* 點擊效果 */
    .smile-button:active {
      transform: scale(0.95);
    }
    
    /* 浮動動畫 */
    @keyframes float {
      0%, 100% { transform: translateY(0px); }
      50% { transform: translateY(-10px); }
    }
    
    /* 微笑提示框 */
    .smile-tooltip {
      position: absolute;
      bottom: 70px;
      right: 0;
      background: rgba(0, 0, 0, 0.9);
      color: white;
      padding: 8px 16px;
      border-radius: 8px;
      font-size: 14px;
      white-space: nowrap;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.3s ease;
    }
    
    /* 顯示提示框 */
    .smile-button:hover + .smile-tooltip {
      opacity: 1;
    }
    '''
    
    # 添加微笑按鈕的HTML
    smile_button_html = '''
    <!-- 微笑按鈕 -->
    <div class="smile-container">
      <button class="smile-button" onclick="handleSmile()">
        😊
      </button>
      <div class="smile-tooltip">給我們一個微笑！</div>
    </div>
    
    <script>
      // 微笑按鈕功能
      function handleSmile() {
        // 創建微笑動畫
        const smileEmojis = ['😊', '😄', '🥰', '😁', '🤗', '✨', '💖'];
        const button = event.target;
        
        // 隨機選擇表情
        const randomEmoji = smileEmojis[Math.floor(Math.random() * smileEmojis.length)];
        button.textContent = randomEmoji;
        
        // 創建飄浮的笑臉效果
        createFloatingSmile();
        
        // 顯示感謝訊息
        showThankYouMessage();
        
        // 3秒後恢復原始笑臉
        setTimeout(() => {
          button.textContent = '😊';
        }, 3000);
      }
      
      // 創建飄浮的笑臉
      function createFloatingSmile() {
        const smile = document.createElement('div');
        smile.textContent = '😊';
        smile.style.cssText = `
          position: fixed;
          bottom: 80px;
          right: 40px;
          font-size: 40px;
          z-index: 999;
          animation: floatUp 2s ease-out forwards;
        `;
        
        document.body.appendChild(smile);
        
        // 2秒後移除
        setTimeout(() => {
          smile.remove();
        }, 2000);
      }
      
      // 顯示感謝訊息
      function showThankYouMessage() {
        const messages = [
          '謝謝您的微笑！',
          '您的微笑讓世界更美好！',
          '保持微笑，好運會來！',
          '微笑是最好的語言！',
          '您的微笑很有感染力！'
        ];
        
        const message = messages[Math.floor(Math.random() * messages.length)];
        
        // 創建訊息元素
        const messageEl = document.createElement('div');
        messageEl.textContent = message;
        messageEl.style.cssText = `
          position: fixed;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 20px 40px;
          border-radius: 50px;
          font-size: 18px;
          font-weight: bold;
          z-index: 1001;
          animation: messagePopup 0.5s ease-out;
          box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
        `;
        
        document.body.appendChild(messageEl);
        
        // 2秒後淡出並移除
        setTimeout(() => {
          messageEl.style.animation = 'messageFadeOut 0.5s ease-out forwards';
          setTimeout(() => {
            messageEl.remove();
          }, 500);
        }, 2000);
      }
      
      // 添加動畫樣式
      const style = document.createElement('style');
      style.textContent = `
        @keyframes floatUp {
          0% {
            opacity: 1;
            transform: translateY(0) scale(1);
          }
          100% {
            opacity: 0;
            transform: translateY(-100px) scale(1.5);
          }
        }
        
        @keyframes messagePopup {
          0% {
            opacity: 0;
            transform: translate(-50%, -50%) scale(0.5);
          }
          100% {
            opacity: 1;
            transform: translate(-50%, -50%) scale(1);
          }
        }
        
        @keyframes messageFadeOut {
          0% {
            opacity: 1;
            transform: translate(-50%, -50%) scale(1);
          }
          100% {
            opacity: 0;
            transform: translate(-50%, -50%) scale(0.8);
          }
        }
      `;
      document.head.appendChild(style);
    </script>
    '''
    
    # 在樣式部分添加微笑按鈕樣式
    content = content.replace(
        '</style>',
        smile_button_styles + '\n  </style>'
    )
    
    # 在登入頁面的 </form> 後面添加微笑按鈕
    content = content.replace(
        '</form>\n</body>',
        '</form>\n' + smile_button_html + '\n</body>'
    )
    
    # 保存修改後的文件
    with open('enterprise_web_app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 已成功添加微笑按鈕！")
    print("功能說明：")
    print("- 按鈕固定在右下角")
    print("- 點擊會顯示不同的表情")
    print("- 創建飄浮動畫效果")
    print("- 顯示隨機感謝訊息")
    print("- 懸停時顯示提示")

if __name__ == "__main__":
    add_smile_button()
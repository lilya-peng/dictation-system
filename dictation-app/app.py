from flask import Flask, request, jsonify
import os
import time
import pyttsx3
import threading

app = Flask(__name__)

# 创建上传文件夹
os.makedirs('static/uploads', exist_ok=True)

# 全局变量保存当前的听写内容
current_text = ""
current_words = []
current_index = -1

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>简易听写系统</title>
        <style>
            body {
                font-family: 'Microsoft YaHei', Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            h1, h2 {
                color: #2c3e50;
            }
            h1 {
                text-align: center;
            }
            .panel {
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                padding: 20px;
                margin-bottom: 20px;
            }
            textarea {
                width: 100%;
                height: 150px;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 16px;
                resize: vertical;
            }
            input[type="file"], button {
                display: block;
                width: 100%;
                padding: 10px;
                margin: 10px 0;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 16px;
            }
            button {
                background-color: #3498db;
                color: white;
                border: none;
                cursor: pointer;
            }
            button:hover {
                background-color: #2980b9;
            }
            button:disabled {
                background-color: #ccc;
                cursor: not-allowed;
            }
            .word-display {
                margin: 20px 0;
                padding: 15px;
                background-color: #f9f9f9;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 24px;
                text-align: center;
                min-height: 60px;
            }
            .control-buttons {
                display: flex;
                justify-content: space-between;
                margin: 15px 0;
            }
            .control-buttons button {
                flex: 1;
                margin: 0 5px;
            }
            .status {
                margin-top: 10px;
                color: #666;
                font-style: italic;
            }
            .hidden {
                display: none;
            }
        </style>
    </head>
    <body>
        <h1>简易听写系统</h1>
        
        <!-- 文本输入面板 -->
        <div class="panel">
            <h2>输入听写内容</h2>
            <textarea id="dictationText" placeholder="在此输入要听写的文本..."></textarea>
            <button id="saveTextBtn">保存听写内容</button>
            <p class="status" id="saveStatus"></p>
        </div>
        
        <!-- 听写面板 -->
        <div class="panel">
            <h2>听写练习</h2>
            <div class="word-display" id="currentWord"></div>
            
            <div class="control-buttons">
                <button id="startBtn" disabled>开始听写</button>
                <button id="repeatBtn" disabled>重复当前</button>
                <button id="nextBtn" disabled>下一个</button>
                <button id="finishBtn" disabled>完成听写</button>
            </div>
            
            <p class="status" id="dictationStatus">请先输入听写内容</p>
        </div>
        
        <!-- 检查结果面板 -->
        <div class="panel">
            <h2>检查结果</h2>
            <textarea id="userAnswer" placeholder="在此输入您的答案以进行比对..."></textarea>
            <button id="checkBtn">检查结果</button>
            
            <div id="resultArea" class="hidden">
                <h3>比对结果：</h3>
                <div id="comparisonResult"></div>
            </div>
        </div>
        
        <script>
            // 使用Web Speech API朗读文本
            function speakTextInBrowser(text) {
                // 检查浏览器是否支持语音合成
                if ('speechSynthesis' in window) {
                    // 取消任何正在进行的朗读
                    window.speechSynthesis.cancel();
                    
                    // 创建一个新的语音对象
                    var utterance = new SpeechSynthesisUtterance(text);
                    
                    // 尝试设置为中文声音
                    utterance.lang = 'zh-CN';
                    
                    // 设置音量、语速和音调
                    utterance.volume = 1;  // 0 到 1
                    utterance.rate = 1;    // 0.1 到 10
                    utterance.pitch = 1;   // 0 到 2
                    
                    // 朗读文本
                    window.speechSynthesis.speak(utterance);
                    
                    console.log("浏览器朗读:", text);
                    return true;
                } else {
                    console.log("浏览器不支持语音合成");
                    return false;
                }
            }
            
            // 保存听写内容
            document.getElementById('saveTextBtn').addEventListener('click', function() {
                const text = document.getElementById('dictationText').value.trim();
                if (!text) {
                    document.getElementById('saveStatus').textContent = '请输入内容';
                    return;
                }
                
                fetch('/api/save-text', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ text: text })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('saveStatus').textContent = '内容已保存';
                        document.getElementById('startBtn').disabled = false;
                    } else {
                        document.getElementById('saveStatus').textContent = '保存失败: ' + data.error;
                    }
                })
                .catch(error => {
                    document.getElementById('saveStatus').textContent = '请求出错: ' + error;
                });
            });
            
            // 开始听写
            document.getElementById('startBtn').addEventListener('click', function() {
                fetch('/api/start-dictation')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('dictationStatus').textContent = `准备开始，共 ${data.total_words} 个词`;
                        document.getElementById('startBtn').disabled = true;
                        document.getElementById('repeatBtn').disabled = false;
                        document.getElementById('nextBtn').disabled = false;
                        document.getElementById('finishBtn').disabled = false;
                        
                        // 读取第一个词
                        getAndSpeakNextWord();
                    } else {
                        document.getElementById('dictationStatus').textContent = '启动失败: ' + data.error;
                    }
                })
                .catch(error => {
                    document.getElementById('dictationStatus').textContent = '请求出错: ' + error;
                });
            });
            
            // 获取并朗读下一个词
            function getAndSpeakNextWord() {
                fetch('/api/next-word')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('currentWord').textContent = data.word;
                        document.getElementById('dictationStatus').textContent = `正在读第 ${data.index + 1} 个词，共 ${data.total} 个`;
                        
                        // 使用浏览器朗读功能
                        speakTextInBrowser(data.word);
                        
                        if (data.is_last) {
                            document.getElementById('nextBtn').disabled = true;
                        }
                    } else {
                        document.getElementById('dictationStatus').textContent = data.error;
                        if (data.finished) {
                            document.getElementById('currentWord').textContent = '听写完成';
                            document.getElementById('nextBtn').disabled = true;
                            document.getElementById('repeatBtn').disabled = true;
                        }
                    }
                })
                .catch(error => {
                    document.getElementById('dictationStatus').textContent = '请求出错: ' + error;
                });
            }
            
            // 重复当前词
            document.getElementById('repeatBtn').addEventListener('click', function() {
                fetch('/api/repeat-word')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('dictationStatus').textContent = `重复第 ${data.index + 1} 个词`;
                        
                        // 使用浏览器朗读功能
                        speakTextInBrowser(data.word);
                    } else {
                        document.getElementById('dictationStatus').textContent = '重复失败: ' + data.error;
                    }
                })
                .catch(error => {
                    document.getElementById('dictationStatus').textContent = '请求出错: ' + error;
                });
            });
            
            // 下一个词
            document.getElementById('nextBtn').addEventListener('click', function() {
                getAndSpeakNextWord();
            });
            
            // 完成听写
            document.getElementById('finishBtn').addEventListener('click', function() {
                document.getElementById('dictationStatus').textContent = '听写已完成，请在下方输入您的答案进行检查';
                document.getElementById('startBtn').disabled = false;
                document.getElementById('repeatBtn').disabled = true;
                document.getElementById('nextBtn').disabled = true;
                document.getElementById('finishBtn').disabled = true;
                document.getElementById('currentWord').textContent = '听写结束';
            });
            
            // 检查结果
            document.getElementById('checkBtn').addEventListener('click', function() {
                const answer = document.getElementById('userAnswer').value.trim();
                if (!answer) {
                    alert('请输入您的答案');
                    return;
                }
                
                fetch('/api/check-answer', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ answer: answer })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('comparisonResult').innerHTML = data.result_html;
                        document.getElementById('resultArea').classList.remove('hidden');
                    } else {
                        alert('检查失败: ' + data.error);
                    }
                })
                .catch(error => {
                    alert('请求出错: ' + error);
                });
            });
        </script>
    </body>
    </html>
    '''

# API端点：保存文本
@app.route('/api/save-text', methods=['POST'])
def save_text():
    global current_text, current_words, current_index
    
    try:
        data = request.json
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({'success': False, 'error': '文本不能为空'})
        
        # 保存文本
        current_text = text
        # 将文本分词（简单按空格分割）
        current_words = text.split()
        current_index = -1
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# API端点：开始听写
@app.route('/api/start-dictation')
def start_dictation():
    global current_index
    
    if not current_words:
        return jsonify({'success': False, 'error': '没有可听写的内容'})
    
    # 重置索引
    current_index = -1
    
    return jsonify({'success': True, 'total_words': len(current_words)})

# API端点：获取下一个词
@app.route('/api/next-word')
def next_word():
    global current_index
    
    if not current_words:
        return jsonify({'success': False, 'error': '没有可听写的内容'})
    
    current_index += 1
    
    if current_index >= len(current_words):
        return jsonify({
            'success': False, 
            'error': '已到达最后一个词', 
            'finished': True
        })
    
    word = current_words[current_index]
    
    return jsonify({
        'success': True,
        'word': word,
        'index': current_index,
        'total': len(current_words),
        'is_last': current_index == len(current_words) - 1
    })

# API端点：重复当前词
@app.route('/api/repeat-word')
def repeat_word():
    if not current_words or current_index < 0 or current_index >= len(current_words):
        return jsonify({'success': False, 'error': '没有当前词可重复'})
    
    word = current_words[current_index]
    
    return jsonify({
        'success': True,
        'word': word,
        'index': current_index
    })

# API端点：检查答案
@app.route('/api/check-answer', methods=['POST'])
def check_answer():
    try:
        data = request.json
        answer = data.get('answer', '').strip()
        
        if not answer:
            return jsonify({'success': False, 'error': '答案不能为空'})
        
        if not current_text:
            return jsonify({'success': False, 'error': '没有原始文本进行比对'})
        
        # 简单比对（可以根据需要改进）
        original_words = current_text.split()
        answer_words = answer.split()
        
        # 生成HTML比对结果
        result_html = '<div style="margin-bottom: 15px;"><strong>原文:</strong><br>'
        
        # 添加原文
        result_html += current_text
        result_html += '</div>'
        
        # 添加用户答案
        result_html += '<div><strong>您的答案:</strong><br>'
        result_html += answer
        result_html += '</div>'
        
        # 统计正确率
        min_len = min(len(original_words), len(answer_words))
        correct_count = 0
        
        for i in range(min_len):
            if original_words[i] == answer_words[i]:
                correct_count += 1
        
        accuracy = round((correct_count / len(original_words)) * 100, 2)
        
        result_html += f'<div style="margin-top: 15px;"><strong>正确率:</strong> {accuracy}%</div>'
        
        # 添加错误列表
        errors = []
        for i in range(min_len):
            if original_words[i] != answer_words[i]:
                errors.append({
                    'index': i,
                    'original': original_words[i],
                    'answer': answer_words[i]
                })
        
        if len(answer_words) < len(original_words):
            for i in range(len(answer_words), len(original_words)):
                errors.append({
                    'index': i,
                    'original': original_words[i],
                    'answer': '缺失'
                })
        
        if errors:
            result_html += '<div style="margin-top: 15px;"><strong>错误列表:</strong><ul>'
            for error in errors:
                result_html += f'<li>第 {error["index"] + 1} 个词: 原文 "{error["original"]}" - 您的答案 "{error["answer"]}"</li>'
            result_html += '</ul></div>'
        else:
            result_html += '<div style="margin-top: 15px; color: green;"><strong>太棒了！没有错误。</strong></div>'
        
        return jsonify({
            'success': True,
            'result_html': result_html,
            'accuracy': accuracy
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
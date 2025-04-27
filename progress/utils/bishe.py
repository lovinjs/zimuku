import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
import torch
import torch.nn as nn
import torch.optim as optim
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json
import os
from django.conf import settings
from datetime import datetime

file_dir = os.path.join(settings.BASE_DIR, 'progress', 'static')
os.makedirs(file_dir, exist_ok=True)

class BiShe:
    # 单例
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(BiShe, cls).__new__(cls)
        return cls._instance

    def __init__(self, file_path=None, websocket=None):
        """
        初始化读取文件路径与 websocket 实例
        """
        if not hasattr(self, '_initialized'):
            if file_path is not None:
                self.file_path = file_path
                self.save_file_path = None
            if websocket is not None:
                self.websocket = websocket
            if file_path is not None:
                self.file_path = file_path
            self._initialized = True  # 标记初始化


    def _send_message(self, content, file_name=''):
        """
        socket 发送消息
        """
        if self.websocket:
            content = {'content': content, 'file': file_name}
            try:
                self.websocket.send(json.dumps(content))
            except Exception as e:
                print(f"socket进度消息发送失败: {str(e)}")

    def excute_training(self):
        """
        执行训练
        """
        # 设置中文显示和随机种子
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False
        np.random.seed(42)
        torch.manual_seed(42)

        # ### 1. 加载数据
        data = pd.read_excel(self.file_path)
        data['Date'] = pd.to_datetime(data['Date'])
        data.set_index('Date', inplace=True)
        data = data.resample('D').interpolate(method='linear').reset_index()

        # 检查原始数据范围
        print(
            f"原始数据性别比例范围：{data['Sex Ratio (Male Proportion)'].min()} 到 {data['Sex Ratio (Male Proportion)'].max()}"
        )
        self._send_message(
            f"原始数据性别比例范围：{data['Sex Ratio (Male Proportion)'].min()} 到 {data['Sex Ratio (Male Proportion)'].max()}"
        )
        print(
            f"原始数据温度范围：{data['Temperature (°C)'].min()} 到 {data['Temperature (°C)'].max()}"
        )
        self._send_message(
            f"原始数据温度范围：{data['Temperature (°C)'].min()} 到 {data['Temperature (°C)'].max()}"
        )
        print(
            f"原始数据降水量范围：{data['Precipitation (mm)'].min()} 到 {data['Precipitation (mm)'].max()}"
        )
        self._send_message(
            f"原始数据降水量范围：{data['Precipitation (mm)'].min()} 到 {data['Precipitation (mm)'].max()}"
        )

        # ### 2. 特征工程
        data['Month'] = data['Date'].dt.month
        data['Day'] = data['Date'].dt.day
        data['Month_sin'] = np.sin(2 * np.pi * data['Month'] / 12)
        data['Month_cos'] = np.cos(2 * np.pi * data['Month'] / 12)
        for lag in [1, 7, 30, 60, 90]:
            data[f'Lag_{lag}'] = data['Sex Ratio (Male Proportion)'].shift(lag)
        data['Rolling_mean_7'] = data['Sex Ratio (Male Proportion)'].rolling(window=7, min_periods=1).mean()
        data['Rolling_std_7'] = data['Sex Ratio (Male Proportion)'].rolling(window=7, min_periods=1).std()
        data['Rolling_mean_30'] = data['Sex Ratio (Male Proportion)'].rolling(window=30, min_periods=1).mean()
        data['Weekday'] = data['Date'].dt.weekday
        data['Temperature'] = data['Temperature (°C)']  # 保留温度特征
        data['Precipitation'] = data['Precipitation (mm)']  # 添加降水量特征
        data = data.dropna()

        # 计算历史温度和降水量的月平均值
        data['month'] = data['Date'].dt.month
        monthly_avg_temp = data.groupby('month')['Temperature'].mean()
        monthly_avg_precip = data.groupby('month')['Precipitation'].mean()

        # 更新特征矩阵，减少时间特征并添加降水量
        features = data[['Month_sin', 'Month_cos', 'Weekday', 'Temperature', 'Precipitation',
                         'Lag_1', 'Lag_7', 'Lag_30', 'Lag_60', 'Lag_90', 'Rolling_mean_7', 'Rolling_std_7',
                         'Rolling_mean_30']]
        target = data['Sex Ratio (Male Proportion)'].values.reshape(-1, 1)

        # ### 3. 归一化
        scaler_features = MinMaxScaler()
        scaler_target = MinMaxScaler()
        features_scaled = scaler_features.fit_transform(features)
        target_scaled = scaler_target.fit_transform(target)

        # ### 4. 准备时间序列数据
        def create_sequences(features, target, seq_length):
            X, y = [], []
            for i in range(len(features) - seq_length):
                X.append(features[i:i + seq_length])
                y.append(target[i + seq_length])
            return np.array(X), np.array(y)

        seq_length = 60
        X_lstm, y_lstm = create_sequences(features_scaled, target_scaled, seq_length)

        # 划分数据集
        total_size = len(X_lstm)
        train_size = int(total_size * 0.7)
        val_size = int(total_size * 0.15)
        test_size = total_size - train_size - val_size

        X_train_lstm = torch.tensor(X_lstm[:train_size], dtype=torch.float32)
        X_val_lstm = torch.tensor(X_lstm[train_size:train_size + val_size], dtype=torch.float32)
        X_test_lstm = torch.tensor(X_lstm[train_size + val_size:], dtype=torch.float32)
        y_train_lstm = torch.tensor(y_lstm[:train_size], dtype=torch.float32)
        y_val_lstm = torch.tensor(y_lstm[train_size:train_size + val_size], dtype=torch.float32)
        y_test_lstm = torch.tensor(y_lstm[train_size + val_size:], dtype=torch.float32)

        # ### 5. 定义单向LSTM模型
        class LSTMModel(nn.Module):
            def __init__(self, input_size, hidden_size, output_size):
                super(LSTMModel, self).__init__()
                self.lstm = nn.LSTM(input_size, hidden_size, batch_first=True, bidirectional=False)
                self.dropout = nn.Dropout(0.2)
                self.fc = nn.Linear(hidden_size, output_size)

            def forward(self, x):
                output, _ = self.lstm(x)
                output = self.dropout(output[:, -1, :])
                output = self.fc(output)
                return output

        input_size = features_scaled.shape[1]  # 更新后的特征数量
        hidden_size = 100
        output_size = 1
        model_lstm = LSTMModel(input_size, hidden_size, output_size)
        criterion = nn.MSELoss()
        optimizer = optim.Adam(model_lstm.parameters(), lr=0.001)

        # ### 6. 训练LSTM
        batch_size = 32
        num_epochs = 100
        patience = 10
        best_val_loss = float('inf')
        counter = 0

        for epoch in range(num_epochs):
            model_lstm.train()
            for i in range(0, len(X_train_lstm), batch_size):
                batch_X = X_train_lstm[i:i + batch_size]
                batch_y = y_train_lstm[i:i + batch_size]
                optimizer.zero_grad()
                outputs = model_lstm(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()

            model_lstm.eval()
            with torch.no_grad():
                val_outputs = model_lstm(X_val_lstm)
                val_loss = criterion(val_outputs, y_val_lstm)

            if (epoch + 1) % 10 == 0:
                print(
                    f'Epoch [{epoch + 1}/{num_epochs}], Train Loss: {loss.item():.6f}, Val Loss: {val_loss.item():.6f}'
                )
                self._send_message(
                    f'Epoch [{epoch + 1}/{num_epochs}], Train Loss: {loss.item():.6f}, Val Loss: {val_loss.item():.6f}'
                )

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                counter = 0
                torch.save(model_lstm.state_dict(), 'best_lstm_model.pth')
            else:
                counter += 1
                if counter >= patience:
                    print(f"Early stopping at epoch {epoch + 1}")
                    self._send_message(f"Early stopping at epoch {epoch + 1}")
                    break

        # 加载最佳模型
        model_lstm.load_state_dict(torch.load('best_lstm_model.pth'))
        model_lstm.eval()
        with torch.no_grad():
            y_pred_lstm_val = model_lstm(X_val_lstm).numpy()
            y_pred_lstm_test = model_lstm(X_test_lstm).numpy()
        mse_lstm_val = mean_squared_error(y_val_lstm.numpy(), y_pred_lstm_val)
        mse_lstm_test = mean_squared_error(y_test_lstm.numpy(), y_pred_lstm_test)
        print(f"LSTM 验证集 MSE: {mse_lstm_val}")
        self._send_message(f"LSTM 验证集 MSE: {mse_lstm_val}")
        print(f"LSTM 测试集 MSE: {mse_lstm_test}")
        self._send_message(f"LSTM 测试集 MSE: {mse_lstm_test}")

        # ### 7. 训练随机森林
        X_rf = features_scaled[seq_length:]
        y_rf = target_scaled[seq_length:]
        X_train_rf = X_rf[:train_size]
        X_val_rf = X_rf[train_size:train_size + val_size]
        X_test_rf = X_rf[train_size + val_size:]
        y_train_rf = y_rf[:train_size]
        y_val_rf = y_rf[train_size:train_size + val_size]
        y_test_rf = y_rf[train_size + val_size:]

        model_rf = RandomForestRegressor(n_estimators=200, max_depth=15, random_state=42)
        model_rf.fit(X_train_rf, y_train_rf.ravel())
        y_pred_rf_val = model_rf.predict(X_val_rf).reshape(-1, 1)
        y_pred_rf_test = model_rf.predict(X_test_rf).reshape(-1, 1)
        mse_rf_val = mean_squared_error(y_val_rf, y_pred_rf_val)
        mse_rf_test = mean_squared_error(y_test_rf, y_pred_rf_test)
        print(f"RF 验证集 MSE: {mse_rf_val}")
        self._send_message(f"RF 验证集 MSE: {mse_rf_val}")
        print(f"RF 测试集 MSE: {mse_rf_test}")
        self._send_message(f"RF 测试集 MSE: {mse_rf_test}")

        # ### 8. 加权融合
        E_lstm_val = mse_lstm_val
        E_rf_val = mse_rf_val
        w_lstm = E_rf_val / (E_lstm_val + E_rf_val) if (E_lstm_val + E_rf_val) != 0 else 0.5
        w_rf = E_lstm_val / (E_lstm_val + E_rf_val) if (E_lstm_val + E_rf_val) != 0 else 0.5
        y_pred_lstm_test_inv = scaler_target.inverse_transform(y_pred_lstm_test)
        y_pred_rf_test_inv = scaler_target.inverse_transform(y_pred_rf_test)
        y_test_original = scaler_target.inverse_transform(y_test_lstm.numpy())
        final_predictions = w_lstm * y_pred_lstm_test_inv + w_rf * y_pred_rf_test_inv
        print(f"LSTM 权重: {w_lstm:.4f}, RF 权重: {w_rf:.4f}")
        self._send_message(f"LSTM 权重: {w_lstm:.4f}, RF 权重: {w_rf:.4f}")
        mse_final = mean_squared_error(y_test_original, final_predictions)
        print(f"最终模型测试集 MSE（反归一化后）: {mse_final}")
        self._send_message(f"最终模型测试集 MSE（反归一化后）: {mse_final}")

        # ### 9. 可视化
        test_dates = data['Date'].iloc[seq_length + train_size + val_size:].values
        plt.figure(figsize=(14, 7))
        plt.plot(test_dates, y_test_original, label='真实值', color='black', linewidth=2)
        plt.plot(test_dates, final_predictions, label='最终预测', color='red', linewidth=2)
        plt.xlabel('日期')
        plt.ylabel('性别比例')
        plt.title('测试集上的最终预测效果')
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        img_name = f"{timestamp}_final_prediction_effect.png"
        plt.savefig(os.path.join(file_dir, img_name), dpi=300)
        print("测试集上的最终预测效果图表已生成！")
        self._send_message("测试集上的最终预测效果图表已生成！", img_name)


        # ### 10. 预测未来60天
        future_days = 60
        last_date = data['Date'].iloc[-1]
        future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=future_days, freq='D')
        future_data = pd.DataFrame({'Date': future_dates})

        # 为未来日期分配历史月平均温度和降水量
        future_data['Month'] = future_data['Date'].dt.month
        future_data['Temperature'] = future_data['Month'].map(monthly_avg_temp)
        future_data['Precipitation'] = future_data['Month'].map(monthly_avg_precip)

        future_data['Day'] = future_data['Date'].dt.day
        future_data['Month_sin'] = np.sin(2 * np.pi * future_data['Month'] / 12)
        future_data['Month_cos'] = np.cos(2 * np.pi * future_data['Month'] / 12)
        future_data['Weekday'] = future_data['Date'].dt.weekday

        future_predictions = []
        current_sequence_scaled = features_scaled[-seq_length:]
        temp_data = data.copy()

        step_size = 15
        for start in range(0, future_days, step_size):
            end = min(start + step_size, future_days)

            for i in range(start, end):
                basic_features = future_data.iloc[i][
                    ['Month_sin', 'Month_cos', 'Weekday', 'Temperature', 'Precipitation']].values

                if i == 0:
                    lag_1 = temp_data['Sex Ratio (Male Proportion)'].iloc[-1]
                    lag_7 = temp_data['Sex Ratio (Male Proportion)'].iloc[-7] if len(temp_data) >= 7 else lag_1
                    lag_30 = temp_data['Sex Ratio (Male Proportion)'].iloc[-30] if len(temp_data) >= 30 else lag_1
                    lag_60 = temp_data['Sex Ratio (Male Proportion)'].iloc[-60] if len(temp_data) >= 60 else lag_1
                    lag_90 = temp_data['Sex Ratio (Male Proportion)'].iloc[-90] if len(temp_data) >= 90 else lag_1
                else:
                    lag_1 = future_predictions[-1]
                    lag_7 = np.mean(future_predictions[-7:]) if i >= 7 else np.mean(
                        temp_data['Sex Ratio (Male Proportion)'].tail(7 - i).tolist() + future_predictions[:i])
                    lag_30 = np.mean(future_predictions[-30:]) if i >= 30 else np.mean(
                        temp_data['Sex Ratio (Male Proportion)'].tail(30 - i).tolist() + future_predictions[:i])
                    lag_60 = np.mean(future_predictions[-60:]) if i >= 60 else np.mean(
                        temp_data['Sex Ratio (Male Proportion)'].tail(60 - i).tolist() + future_predictions[:i])
                    lag_90 = np.mean(future_predictions[-90:]) if i >= 90 else np.mean(
                        temp_data['Sex Ratio (Male Proportion)'].tail(90 - i).tolist() + future_predictions[:i])

                recent_data_7 = temp_data['Sex Ratio (Male Proportion)'].tail(
                    max(7 - i, 0)).tolist() + future_predictions[:i]
                recent_data_30 = temp_data['Sex Ratio (Male Proportion)'].tail(
                    max(30 - i, 0)).tolist() + future_predictions[:i]
                rolling_mean_7 = np.mean(recent_data_7[-7:]) if len(recent_data_7) >= 7 else np.mean(recent_data_7)
                rolling_std_7 = np.std(recent_data_7[-7:]) if len(recent_data_7) >= 7 else np.std(
                    recent_data_7) if len(recent_data_7) > 1 else 0
                rolling_mean_30 = np.mean(recent_data_30[-30:]) if len(recent_data_30) >= 30 else np.mean(
                    recent_data_30)

                current_features = np.concatenate([basic_features, [lag_1, lag_7, lag_30, lag_60, lag_90,
                                                                    rolling_mean_7, rolling_std_7,
                                                                    rolling_mean_30]])
                current_features_scaled = scaler_features.transform([current_features])

                current_sequence_scaled = np.vstack([current_sequence_scaled[1:], current_features_scaled])
                current_sequence_tensor = torch.tensor(current_sequence_scaled, dtype=torch.float32).unsqueeze(0)
                with torch.no_grad():
                    pred_lstm_scaled = model_lstm(current_sequence_tensor).item()
                pred_lstm = scaler_target.inverse_transform([[pred_lstm_scaled]])[0][0]
                pred_rf_scaled = model_rf.predict(current_features_scaled)[0]
                pred_rf = scaler_target.inverse_transform([[pred_rf_scaled]])[0][0]
                pred = w_lstm * pred_lstm + w_rf * pred_rf
                pred = min(max(pred, 0), 0.8)  # 限制预测值在 [0, 0.8]
                future_predictions.append(pred)
                print(f"Day {i + 1}: Predicted Sex Ratio = {pred}")
                self._send_message(f"Day {i + 1}: Predicted Sex Ratio = {pred}")

            new_rows = pd.DataFrame({
                'Date': future_dates[start:end],
                'Sex Ratio (Male Proportion)': future_predictions[start:end]
            })
            temp_data = pd.concat([temp_data, new_rows], ignore_index=True)

        future_predictions_smoothed = pd.Series(future_predictions).rolling(window=5, min_periods=1).mean().tolist()

        results = pd.DataFrame({'Date': future_dates, 'Predicted Sex Ratio': future_predictions_smoothed})
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_name = f"{timestamp}_future_predictions.xlsx"
        results.to_excel(os.path.join(file_dir, file_name), index=False)
        self.save_file_path = os.path.join(file_dir, file_name)
        print("未来60天的预测结果已保存")
        self._send_message("未来60天的预测结果已保存", file_name)

        # ### 10. 可视化未来365天的预测结果
        plt.figure(figsize=(14, 7))
        plt.plot(future_dates, future_predictions_smoothed, label='预测性别比例', color='blue', linewidth=2)
        plt.xlabel('日期')
        plt.ylabel('性别比例')
        plt.title('未来365天性别比例预测')
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        img_name = f"{timestamp}_future_sex_ratio.png"
        plt.savefig(os.path.join(file_dir, img_name), dpi=300)
        print("未来365天性别比例预测图表已生成！")
        self._send_message("未来365天性别比例预测图表已生成！", img_name)

    def query_sex_ratio(self, date_str):
        df = pd.read_excel(self.save_file_path)
        df["Date"] = pd.to_datetime(df["Date"]).dt.date
        search_date = pd.to_datetime(date_str).date()
        matched_row = df[df["Date"] == search_date]
        if not matched_row.empty:
            sex_ratio = matched_row["Predicted Sex Ratio"].values[0]
            return sex_ratio
        else:
            return None

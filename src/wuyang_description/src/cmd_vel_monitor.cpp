#include <atomic>
#include <chrono>
#include <mutex>
#include <thread>

#include <QApplication>
#include <QFont>
#include <QFrame>
#include <QLabel>
#include <QTimer>
#include <QVBoxLayout>
#include <QWidget>

#include "geometry_msgs/msg/twist.hpp"
#include "rclcpp/rclcpp.hpp"

// ── 线程共享数据 ────────────────────────────────────────────────
struct SharedData {
    std::mutex mtx;
    bool ever_received{false};
    std::chrono::steady_clock::time_point last_recv;
    double last_interval_ms{-1.0};  // 相邻两帧间隔
};

// ── ROS2 订阅节点 ────────────────────────────────────────────────
class MonitorNode : public rclcpp::Node
{
public:
    explicit MonitorNode(std::shared_ptr<SharedData> data)
    : Node("cmd_vel_monitor"), data_(data)
    {
        sub_ = create_subscription<geometry_msgs::msg::Twist>(
            "/cmd_vel", 10,
            [this](const geometry_msgs::msg::Twist::SharedPtr /*msg*/) {
                auto now = std::chrono::steady_clock::now();
                std::lock_guard<std::mutex> lk(data_->mtx);
                if (data_->ever_received) {
                    data_->last_interval_ms =
                        std::chrono::duration<double, std::milli>(
                            now - data_->last_recv).count();
                }
                data_->last_recv = now;
                data_->ever_received = true;
            });
    }

private:
    rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr sub_;
    std::shared_ptr<SharedData> data_;
};

// ── Qt 监控弹窗 ──────────────────────────────────────────────────
class MonitorWidget : public QWidget
{
    Q_OBJECT

public:
    explicit MonitorWidget(std::shared_ptr<SharedData> data,
                           QWidget *parent = nullptr)
    : QWidget(parent), data_(data)
    {
        setWindowTitle("/cmd_vel 延迟监控");
        setFixedSize(420, 220);

        auto *root = new QVBoxLayout(this);
        root->setContentsMargins(20, 16, 20, 16);
        root->setSpacing(8);

        // ── 消息距今 ──
        age_label_ = make_label(20, true);
        age_label_->setText("等待 /cmd_vel 消息…");

        // ── 消息间隔 ──
        interval_label_ = make_label(13, false);

        // ── 分隔线 ──
        auto *line = new QFrame(this);
        line->setFrameShape(QFrame::HLine);
        line->setFrameShadow(QFrame::Sunken);

        // ── 延迟评级 ──
        rating_label_ = make_label(15, true);

        // ── 说明 ──
        auto *hint = make_label(10, false);
        hint->setText(
            "* 消息距今 = 上帧到达至今的时间（消息新鲜度）\n"
            "  若需真实网络RTT，请改用 TwistStamped 并附上发送时间戳");
        hint->setStyleSheet("color: #888;");
        hint->setWordWrap(true);

        root->addWidget(age_label_);
        root->addWidget(interval_label_);
        root->addWidget(line);
        root->addWidget(rating_label_);
        root->addWidget(hint);

        auto *timer = new QTimer(this);
        connect(timer, &QTimer::timeout, this, &MonitorWidget::refresh);
        timer->start(100);   // 10 Hz 刷新
    }

private slots:
    void refresh()
    {
        double age_ms, interval_ms;
        bool ok;
        {
            std::lock_guard<std::mutex> lk(data_->mtx);
            ok = data_->ever_received;
            if (!ok) return;
            age_ms = std::chrono::duration<double, std::milli>(
                std::chrono::steady_clock::now() - data_->last_recv).count();
            interval_ms = data_->last_interval_ms;
        }

        age_label_->setText(
            QString("消息距今：<b>%1 ms</b>").arg(age_ms, 0, 'f', 1));

        if (interval_ms > 0.0) {
            interval_label_->setText(
                QString("消息间隔：%1 ms　　频率：%2 Hz")
                    .arg(interval_ms, 0, 'f', 1)
                    .arg(1000.0 / interval_ms, 0, 'f', 1));
        }

        // ── 延迟评级（基于消息距今） ──────────────────────────
        struct Grade { double threshold; const char *text; const char *color; };
        static constexpr Grade grades[] = {
            {  50.0, "● 优秀   — 实时同步  (< 50 ms)",   "#00c853" },
            { 100.0, "● 良好   — 轻微延迟  (50–100 ms)",  "#76d275" },
            { 200.0, "● 可接受 — 明显延迟  (100–200 ms)", "#ffd600" },
            { 500.0, "● 较差   — 严重延迟  (200–500 ms)", "#ff6d00" },
            {  1e9,  "● 断连   — 消息中断  (> 500 ms)",   "#d50000" },
        };

        for (auto &g : grades) {
            if (age_ms < g.threshold) {
                rating_label_->setText(g.text);
                rating_label_->setStyleSheet(
                    QString("color: %1; font-weight: bold;").arg(g.color));
                break;
            }
        }
    }

private:
    QLabel *make_label(int pt, bool bold)
    {
        auto *l = new QLabel(this);
        l->setAlignment(Qt::AlignLeft | Qt::AlignVCenter);
        QFont f = l->font();
        f.setPointSize(pt);
        f.setBold(bold);
        l->setFont(f);
        return l;
    }

    std::shared_ptr<SharedData> data_;
    QLabel *age_label_;
    QLabel *interval_label_;
    QLabel *rating_label_;
};

// ── main ─────────────────────────────────────────────────────────
int main(int argc, char *argv[])
{
    rclcpp::init(argc, argv);
    QApplication app(argc, argv);

    auto data = std::make_shared<SharedData>();
    auto node = std::make_shared<MonitorNode>(data);

    // ROS2 spin 跑在独立线程，Qt 事件循环在主线程
    std::thread ros_thread([&node]() { rclcpp::spin(node); });

    MonitorWidget win(data);
    win.show();

    int ret = app.exec();

    rclcpp::shutdown();
    ros_thread.join();
    return ret;
}

#include "cmd_vel_monitor.moc"   // AUTOMOC 需要此行（Q_OBJECT 在 .cpp 中）

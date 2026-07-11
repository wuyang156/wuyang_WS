#include <mutex>
#include <thread>

#include <QApplication>
#include <QFont>
#include <QFrame>
#include <QLabel>
#include <QTime>
#include <QTimer>
#include <QVBoxLayout>
#include <QWidget>

#include "geometry_msgs/msg/twist.hpp"
#include "rclcpp/rclcpp.hpp"

// ── 线程共享数据 ────────────────────────────────────────────────
struct SharedData {
    std::mutex mtx;
    bool ever_received{false};
    double latest_latency_ms{-1.0};  // 最新一条消息：发出 → 接收 的时延
};

// ── ROS2 订阅节点 ────────────────────────────────────────────────
class MonitorNode : public rclcpp::Node
{
public:
    explicit MonitorNode(std::shared_ptr<SharedData> data)
    : Node("cmd_vel_monitor"), data_(data)
    {
        // 带 MessageInfo 的回调：读取 DDS 层时间戳
        //   source_timestamp   —— 发布端 publish() 时自动打戳
        //   received_timestamp —— 接收端收到时打戳
        // 两者之差即为“最近一条消息从发出到被接收”的时延
        sub_ = create_subscription<geometry_msgs::msg::Twist>(
            "/cmd_vel", 10,
            [this](geometry_msgs::msg::Twist::UniquePtr /*msg*/,
                   const rclcpp::MessageInfo & info) {
                const auto & rmw = info.get_rmw_message_info();
                double latency_ms = static_cast<double>(
                    rmw.received_timestamp - rmw.source_timestamp) / 1e6;
                if (latency_ms < 0.0) latency_ms = 0.0;  // 时钟偏差保护

                std::lock_guard<std::mutex> lk(data_->mtx);
                data_->latest_latency_ms = latency_ms;
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
        setWindowTitle("/cmd_vel 网络延迟监控");
        setFixedSize(460, 240);

        auto *root = new QVBoxLayout(this);
        root->setContentsMargins(24, 18, 24, 18);
        root->setSpacing(10);

        latency_label_ = make_label(22, true);
        latency_label_->setText("等待 /cmd_vel 消息…");

        auto *line = new QFrame(this);
        line->setFrameShape(QFrame::HLine);
        line->setFrameShadow(QFrame::Sunken);

        rating_label_ = make_label(15, true);
        update_label_ = make_label(10, false);
        update_label_->setStyleSheet("color: #888;");

        auto *hint = make_label(10, false);
        hint->setText(
            "* 延迟 = DDS received_timestamp − source_timestamp\n"
            "  跨机器测量需两端 NTP 时钟同步，否则值含时钟偏差\n"
            "* 每 2 秒采样一次最新消息的时延");
        hint->setStyleSheet("color: #888;");
        hint->setWordWrap(true);

        root->addWidget(latency_label_);
        root->addWidget(line);
        root->addWidget(rating_label_);
        root->addWidget(update_label_);
        root->addWidget(hint);

        // 每 2 秒采样并刷新一次
        auto *timer = new QTimer(this);
        connect(timer, &QTimer::timeout, this, &MonitorWidget::refresh);
        timer->start(2000);
    }

private slots:
    void refresh()
    {
        double latency_ms;
        bool ok;
        {
            std::lock_guard<std::mutex> lk(data_->mtx);
            ok = data_->ever_received;
            latency_ms = data_->latest_latency_ms;
        }
        if (!ok) return;

        latency_label_->setText(
            QString("网络延迟：<b>%1 ms</b>").arg(latency_ms, 0, 'f', 2));

        // ── 延迟评级 ──────────────────────────────────────────
        struct Grade { double hi; const char *text; const char *color; };
        static constexpr Grade grades[] = {
            {  20.0, "● 优秀   — 实时控制    (< 20 ms)",    "#00c853" },
            {  50.0, "● 良好   — 轻微延迟    (20–50 ms)",   "#76d275" },
            { 100.0, "● 可接受 — 明显延迟    (50–100 ms)",  "#ffd600" },
            { 300.0, "● 较差   — 控制受影响  (100–300 ms)", "#ff6d00" },
            {  1e9,  "● 严重   — 基本不可用  (> 300 ms)",   "#d50000" },
        };
        for (auto &g : grades) {
            if (latency_ms < g.hi) {
                rating_label_->setText(g.text);
                rating_label_->setStyleSheet(
                    QString("color: %1; font-weight: bold;").arg(g.color));
                break;
            }
        }

        update_label_->setText(
            QString("最近采样：%1").arg(QTime::currentTime().toString("hh:mm:ss")));
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
    QLabel *latency_label_;
    QLabel *rating_label_;
    QLabel *update_label_;
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

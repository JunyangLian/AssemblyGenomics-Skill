# InterProScan 预检查修复

2026-09-07。该补丁包不包含 config.json，不会替换已配置的数据库路径。

## 修复内容

1. InterProScan 5 在没有输入时可能显示完整帮助和成员分析列表后以状态 1 退出。原预检查把它误判为命令失败。现在只对显式 `--help` 探测兼容该行为，并验证帮助内容、退出码和常见异常标志；版本命令及实际分析仍要求状态 0。
2. 当前服务器 Java 为 25，官方要求本次使用的 InterProScan 版本采用 Java 11。新增 `java_home` 可选配置；只向 InterProScan 及其 Java 探测子进程传入 JAVA_HOME/PATH，不修改 base 环境或启动文件。
3. 帮助和版本的完整输出保存在 `test/preflight_logs`，错误信息显示退出码、日志路径和输出开头/结尾，避免只留下成员库列表而截掉真正错误。

Phobius、SignalP、TMHMM 的停用信息与帮助退出码分开处理。它们属于需要额外安装/授权的可选分析；本次使用安装中的默认可用成员分析，不自动安装或启用这些可选组件。

## 安装补丁

上传 `Siganus_preflight_fix.zip` 到服务器的 `Siganus_qatar` 项目目录，然后执行：

```bash
cd ~/Siganus_annotation/Siganus_qatar
cp -a test/scripts "test/scripts.backup.$(date +%Y%m%d_%H%M%S)"
unzip -o Siganus_preflight_fix.zip
python3 test/scripts/configure_java11.py
```

Java 工具只在已知的系统、软件及 Conda 安装目录检查候选，执行 `java -version` 后仅选择版本 11；不按目录名猜版本、不自动安装。选中后先备份配置，再写入 Java 根目录。若返回 3，表示在这些位置没有找到可运行的 Java 11，并不表示服务器所有位置都不存在。

如果未找到，可以新建当前用户专用环境。无需激活，也不会修改 base；需要 Conda 软件源可访问：

```bash
conda create -p "$HOME/env/siganus_ipr_java11" -c conda-forge "openjdk=11" -y && \
python3 test/scripts/configure_java11.py --java-home "$HOME/env/siganus_ipr_java11"
```

如果该目录已经是现有环境，不要删除它；先用 `--java-home` 验证。如版本错误，可选择另一个未使用的目录新建。

配置成功后执行：

```bash
if bash test/scripts/check.sh > test/preflight.log 2>&1; then
    cat test/preflight.log
    nohup bash test/scripts/run_all.sh > test/run_all.log 2>&1 &
    echo "测试已启动，PID：$!"
else
    cat test/preflight.log
fi
```

修改的是流程实现，因此原检查点会失效。本次尚未开始真实比对，没有已完成计算需要保留复用。

本地 24 项合成回归测试通过，真实服务器测试仍待执行。

依据：[InterProScan 官方启动代码](https://github.com/ebi-pf-team/interproscan/blob/master/core/jms-implementation/src/main/java/uk/ac/ebi/interpro/scan/jms/main/Run.java)、[官方安装要求与可选分析说明](https://interproscan-docs.readthedocs.io/en/v5/UserDocs.html)。

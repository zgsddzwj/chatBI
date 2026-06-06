import React, { useEffect, useState } from "react";
import { Drawer, List, Button, Tooltip, message, Tag, TagProps } from "antd";
import { useTemplates } from "../hooks/useTemplates";

interface Props {
  open: boolean;
  onClose: () => void;
  onUseTemplate: (question: string) => void;
}

export const TemplateDrawer: React.FC<Props> = ({ open, onClose, onUseTemplate }) => {
  const { templates, removeTemplate } = useTemplates();

  return (
    <Drawer
      title="常用查询收藏夹"
      placement="right"
      onClose={onClose}
      open={open}
      width={360}
      extra={
        <div style={{ fontSize: 13, color: "#9aa0b5" }}>
          共 {templates.length} 个模板
        </div>
      }
    >
      {templates.length === 0 ? (
        <div style={{ color: "#9aa0b5", fontSize: 14, textAlign: "center", marginTop: 48 }}>
          暂无收藏
        </div>
      ) : (
        <List
          dataSource={templates}
          renderItem={(tpl) => {
            const chartType = (tpl.chart as any)?.type;
            const color: TagProps["color"] =
              chartType === "bar" ? "blue" :
              chartType === "line" ? "cyan" :
              chartType === "pie" ? "purple" :
              chartType === "heatmap" ? "orange" :
              chartType === "correlation" ? "magenta" : "default";
            return (
              <List.Item
                actions={[
                  <Tooltip title="使用这个查询">
                    <Button size="small" type="primary" ghost onClick={() => { onUseTemplate(tpl.question); onClose(); }}>
                      使用
                    </Button>
                  </Tooltip>,
                  <Tooltip title="删除">
                    <Button size="small" danger ghost onClick={() => {
                      removeTemplate(tpl.id);
                      message.success("已删除");
                    }}>删除</Button>
                  </Tooltip>
                ]}
              >
                <List.Item.Meta
                  title={<>
                    <span style={{ fontSize: 14 }}>{tpl.summary || tpl.question}</span>
                    {tpl.chart && (
                      <Tag color={color} style={{ marginLeft: 8 }}>{tpl.chart.type}</Tag>
                    )}
                  </>}
                  description={
                    <>
                      <div style={{ fontSize: 13, color: "#9aa0b5", marginTop: 2 }}>
                        {tpl.question}
                      </div>
                      <div style={{ fontSize: 12, color: "#6b7184", marginTop: 4 }}>
                        {new Date(tpl.createdAt).toLocaleString()}
                      </div>
                    </>
                  }
                />
              </List.Item>
            );
          }}
        />
      )}
    </Drawer>
  );
};

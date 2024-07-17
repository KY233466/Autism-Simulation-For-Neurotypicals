import { useState, useCallback, useEffect } from "react";
import { useParams } from "react-router-dom";
import CircularProgress from "@mui/material/CircularProgress";
import Alert from "@mui/material/Alert";
import Collapse from "@mui/material/Collapse";
import IconButton from "@mui/material/IconButton";
import CloseIcon from "@mui/icons-material/Close";

import Header from "../components/header/index.js";
import InputAndMessages from "../components/InputAndMessages/index.js";
import { Post, Get } from "../utils/request.js";

import styles from "./landing.module.css";

const Playground = () => {
  const { conversationIDFromParam } = useParams();
  const [headerHeight, setHeaderHeight] = useState(null);
  const [data, setData] = useState(null);
  const [conversationList, setConversationList] = useState(null);
  const [nextConversation, setNextConversation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [alertMessage, setAlertMessage] = useState("");
  const currentLevel = window.location.href.split("/")[4] - 1;

  const fetchNextSteps = async (conversationID, condition) => {
    const next = await Post(`conversations/${conversationID}/next`, {
      option: "none",
    });
    if (!next.ok) {
      setAlertMessage("Error occurred fetching data");
      return;
    }

    if (condition || next.data.type === "ap") {
      const userOptions = await Post(`conversations/${conversationID}/next`, {
        option: "none",
      });
      if (!userOptions.ok) {
        setAlertMessage("Error occurred fetching data");
        return;
      }

      setNextConversation({
        options: userOptions.data.options,
        ap_message: next.data.content,
      });

      console.log("fetchNextSteps 1", {
        options: userOptions.data.options,
        ap_message: next.data.content,
      });
    } else {
      console.log("fetchNextSteps 2", next.data);
      setNextConversation(next.data);
    }
  };

  const fetchNewConversation = async () => {
    const initConversation = await Post("conversations/", {
      type: "level",
      level: currentLevel,
    });
    if (!initConversation.ok) {
      setAlertMessage("Error occurred fetching data");
      return;
    }
    const initData = initConversation.data;
    setData({
      id: initData.id,
      subject_name: initData.agent,
      topic: initData.info.topic,
      messages: initData.elements,
    });

    await fetchNextSteps(
      initConversation.data.id,
      !initConversation.data.info.scenario.is_user_initiated
    );
  };

  useEffect(() => {
    const fetchData = async () => {
      if (typeof currentLevel !== "number") {
        setAlertMessage("Invalid url parameter");
      }

      const listConversations = await Get(
        `conversations/?type=playground&level=0`
      );
      if (!listConversations.ok) {
        setAlertMessage("Error occurred fetching data");
        return;
      }

      setConversationList(listConversations.data);

      if (listConversations.data.length === 0) {
        await fetchNewConversation();
      } else {
        const conversationID = conversationIDFromParam ||
          listConversations.data[listConversations.data.length - 1].id;

        console.log(conversationIDFromParam, conversationID);
        const history = await Get(`conversations/${conversationID}`);
        if (!history.ok) {
          setAlertMessage("Error occurred fetching data");
          return;
        }
        const historyData = history.data;

        setData({
          id: conversationID,
          subject_name: historyData.agent,
          scenario: historyData.info.scenario,
          topic: historyData.info.topic,
          messages: historyData.elements,
        });

        if (historyData.state === null) {
          await fetchNextSteps(conversationID);
        }
        else if (historyData.state.waiting) {
          console.log(
            "historyData.state.waiting",
            historyData.state.waiting,
          );

          if (historyData.elements.length === 0) {
            setNextConversation({
              options: historyData.state.options
            });
          }
          else {
            setNextConversation({
              options:
                historyData.elements[historyData.elements.length - 1]
                  .type !== "feedback"
                  ? historyData.state.options
                  : [],
            });
          }
        } else {
          await fetchNextSteps(conversationID);
        }
      }

      setLoading(false);
    };

    fetchData();
  }, [conversationIDFromParam, currentLevel]);

  const header = useCallback((node) => {
    if (node !== null) {
      setHeaderHeight(node.getBoundingClientRect().height);
    }
  }, []);

  return (
    <div className={styles.wrapper}>
      {alertMessage && (
        <Collapse in={alertMessage !== ""}>
          <Alert
            action={
              <IconButton
                aria-label="close"
                color="inherit"
                size="small"
                onClick={() => {
                  setAlertMessage(null);
                }}
              >
                <CloseIcon fontSize="inherit" />
              </IconButton>
            }
            sx={{ position: "absolute", top: "20px" }}
            variant="filled"
            severity="warning"
          >
            {alertMessage}
          </Alert>
        </Collapse>
      )}
      {loading ? (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "20px",
            marginBottom: "10%",
          }}
        >
          <CircularProgress />
          <div style={{ color: "white" }}>Building Playground</div>
        </div>
      ) : (
        <div style={{ width: "100%", height: "100%" }}>
          <div ref={header}>
            <Header
              name={data["subject_name"]}
              initData={{
                topic: data["topic"],
              }}
              fetchNewConversation={fetchNewConversation}
              conversationList={conversationList}
              currentLevel={currentLevel}
              showMore={false}
            />
          </div>
          <InputAndMessages
            headerHeight={headerHeight}
            inputPlaceholder={
              "Write your own response or choose an option to send"
            }
            explanationText={null}
            initData={{
              id: data?.id,
              options: nextConversation.options,
              is_user_initiated: data?.scenario?.is_user_initiated,
              ap_message: nextConversation?.ap_message,
              messages: data?.messages || [],
            }}
          />
        </div>
      )}
    </div>
  );
};

export default Playground;
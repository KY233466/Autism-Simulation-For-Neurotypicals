import { useState } from "react";
import Inputs from "../InputSection/index.js";
import Messages from "../messages/index.js";
import LinearProgress from "@mui/material/LinearProgress";
import handleSend from "../InputSection/util/handleSend";

const InputAndMessages = ({ headerHeight, initData }) => {
  const convertToMessageHistory = () => {
    const userName = localStorage.getItem("name");
    return initData.messages.map((m) => {
      if (m.type === 'message') {
        return {
          type: "text",
          isSentByUser: userName === m.content.sender,
          content: m.content.message,
        };
      }
      return {
        type: "feedback",
        content: {
          body: m.content.body,
          title: m.content.title,
          choice: m.content.follow_up,
        },
      };
    });
  };

  const setInitChoice = () => {
    if (initData.messages.length === 0) {
      return '';
    }
    const lastElement = initData.messages[initData.messages.length - 1];
    return lastElement.type === "feedback" ? lastElement.content.follow_up : "";
  };

  const [options, setOptions] = useState(Object.assign({}, initData.options));
  const [chatHistory, setChatHistory] = useState(
    initData.ap_message
      ? [
          ...convertToMessageHistory(),
          {
            type: "text",
            isSentByUser: false,
            content: initData.ap_message,
          },
        ]
      : [...convertToMessageHistory()]
  );
  const [choice, setChoice] = useState(setInitChoice());
  const [selectedButton, setSelectedButton] = useState(0);
  const [showProgress, setShowProgress] = useState(false);

  const handleClickFeedback = (index, message) => {
    setSelectedButton(index);
    setChoice(message);
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: `calc(100% - ${headerHeight}px)`,
      }}
    >
      {showProgress && (
        <LinearProgress sx={{ position: "absolute", width: "100%" }} />
      )}
      <Messages
        chatHistory={chatHistory}
        handleClickFeedback={handleClickFeedback}
        setShowProgress={setShowProgress}
        options={options}
      />
      <Inputs
        handleSend={handleSend(
          chatHistory,
          setChatHistory,
          setShowProgress,
          choice,
          setChoice,
          selectedButton,
          setSelectedButton,
          initData.id
        )}
        choice={choice}
        setChoice={setChoice}
        setSelectedButton={setSelectedButton}
        options={options}
        setOptions={setOptions}
      />
    </div>
  );
};

export default InputAndMessages;
